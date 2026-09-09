"""Evidence-driven two-photo recovery for a single flat document.

Policy planner: inspect -> choose correction or request evidence -> register ->
validate -> copy supported regions -> re-read -> report unresolved regions.
No language model or synthetic character completion is used.
"""
import base64
import re
import time

import cv2
import numpy as np

from app.reading import read, text_of
from app.vision import analyze, data_url, metrics


def decode_url(value):
    return cv2.imdecode(np.frombuffer(base64.b64decode(value.split(',', 1)[1]), np.uint8), cv2.IMREAD_COLOR)


def obstruction(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # A colored object is a suspicion, not proof of occluded text.
    mask = np.uint8((hsv[:, :, 1] > 85) & (hsv[:, :, 2] > 45)) * 255
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))


def intersects(a, b):
    x, y, w, h = a
    X, Y, W, H = b
    return max(0, min(x+w, X+W)-max(x, X)) * max(0, min(y+h, Y+H)-max(y, Y))


def regions_for(page, lines, sharpness):
    h, w = page.shape[:2]
    boxes = []
    contours, _ = cv2.findContours(obstruction(page), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv2.contourArea(contour) > h*w*.002:
            x, y, bw, bh = cv2.boundingRect(contour)
            # Background along the outer edge is not a useful recovery target.
            if bw > w*.9 and bh > h*.9:
                continue
            boxes.append(([max(0,x-12), max(0,y-12), min(w,x+bw+12)-max(0,x-12),
                           min(h,y+bh+12)-max(0,y-12)], 'possible-cover'))
    if sharpness < 45:
        boxes = [([0, 0, w, h], 'blur')]
    else:
        for line in lines:
            if line['uncertain'] and not any(intersects(line['box'], b) for b, _ in boxes):
                x, y, bw, bh = line['box']
                boxes.append(([max(0,x-8),max(0,y-8),min(w,x+bw+8)-max(0,x-8),
                               min(h,y+bh+8)-max(0,y-8)], 'low-ocr-score'))
    labels = {'possible-cover': 'Kemungkinan tertutup / objek berwarna',
              'blur': 'Detail teks terlalu lemah', 'low-ocr-score': 'Bacaan OCR meragukan'}
    return [{'id': f'region-{i+1}', 'box': b, 'reason': why, 'label': labels[why],
             'status': 'unresolved', 'source': 'photo-1'} for i, (b, why) in enumerate(boxes[:30])]


def pack(result, page, lines, regions, started):
    result.update(ocr_available=True, lines=lines, text=text_of(lines), regions=regions,
                  width=page.shape[1], height=page.shape[0],
                  elapsed_ms=round((time.perf_counter()-started)*1000),
                  planner='bounded-policy', sources=[{'id':'photo-1','label':'Foto awal'}])
    unresolved = [r for r in regions if r['status'] == 'unresolved']
    if unresolved:
        result['status'] = 'retake'
        result['instruction'] = ('Ada bagian yang belum dapat diverifikasi. Singkirkan penghalang, ketuk teks untuk fokus, '
                                 'lalu tambahkan foto kedua dari halaman yang sama. Sertakan teks di sekitar area agar dapat dicocokkan.')
    if not lines:
        result['status'] = 'retake'
        result['instruction'] = 'Belum ada teks yang terbaca. Ambil foto lebih tajam dengan keempat sudut halaman terlihat.'
    for line in lines:
        line['unresolved'] = any(intersects(line['box'], r['box']) for r in unresolved)
    return result


def inspect(image):
    started = time.perf_counter()
    result = analyze(image)
    page = decode_url(result['aligned'])
    output = decode_url(result['result'])
    lines = read(output)
    result['before_lines'] = lines if result['aligned']==result['result'] else read(page)
    result['before_text'] = text_of(result['before_lines'])
    regions = regions_for(page, lines, result['before']['sharpness'])
    result['trace'].append({'title':'Membaca teks dengan OCR lokal',
                            'detail':f'{len(lines)} baris terdeteksi. Skor model tidak membuktikan ketepatan isi.'})
    result['trace'].append({'title':'Memilih langkah berikutnya',
                            'detail':f'{len(regions)} area meminta bukti tambahan.' if regions else
                            'Tidak ada area mencurigakan yang terdeteksi. Tetap tinjau angka dan tandai area yang terlewat.'})
    return pack(result, page, lines, regions, started)


def register(first, second):
    sift = cv2.SIFT_create(nfeatures=4500)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_BGR2GRAY), None)
    if d1 is None or d2 is None:
        raise ValueError('Detail bersama tidak cukup. Ambil foto lebih lebar dan tajam, atau ganti foto awal.')
    pairs = cv2.BFMatcher().knnMatch(d2, d1, k=2)
    good = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < .68*b.distance]
    # Do not count several second-photo features matching the same first feature.
    good = list({m.trainIdx:m for m in sorted(good, key=lambda m:m.distance, reverse=True)}.values())
    if len(good) < 16:
        raise ValueError('Foto belum cocok: terlalu sedikit detail yang sama. Sertakan lebih banyak teks di sekitar area.')
    src = np.float32([k2[m.queryIdx].pt for m in good])
    dst = np.float32([k1[m.trainIdx].pt for m in good])
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None or mask is None or not np.isfinite(H).all():
        raise ValueError('Pemetaan kedua foto gagal. Ambil ulang halaman yang sama tanpa melipat kertas.')
    valid = mask.ravel().astype(bool)
    count, ratio = int(valid.sum()), float(valid.mean())
    if count < 14 or ratio < .35:
        raise ValueError('Kecocokan terlalu lemah. Sertakan lebih banyak teks dari halaman yang sama.')
    area = cv2.contourArea(cv2.convexHull(dst[valid])) if count >= 3 else 0
    error = float(np.median(np.linalg.norm(cv2.perspectiveTransform(src[valid,None,:], H)[:,0]-dst[valid], axis=1)))
    sh, sw = second.shape[:2]
    corners = cv2.perspectiveTransform(np.float32([[[0,0],[sw-1,0],[sw-1,sh-1],[0,sh-1]]]), H)[0]
    projected_area = cv2.contourArea(corners)
    fh, fw = first.shape[:2]
    if (count < 14 or ratio < .35 or error > 2 or area < fh*fw*.025 or
            not cv2.isContourConvex(corners) or projected_area < fh*fw*.04 or projected_area > fh*fw*12):
        raise ValueError('Kecocokan geometris belum dapat dipercaya. Gunakan halaman yang sama dan foto dengan area tumpang tindih lebih luas.')
    warped = cv2.warpPerspective(second, H, (fw, fh))
    coverage = cv2.warpPerspective(np.full((sh,sw),255,np.uint8), H, (fw,fh), flags=cv2.INTER_NEAREST)
    coverage = cv2.erode(coverage, np.ones((7,7),np.uint8))
    return warped, coverage, H, {'inliers':count, 'matches':len(good),
                                 'inlier_ratio':round(ratio,3), 'median_error_px':round(error,3)}


def check_identity(old_lines, new_lines):
    """Reject confident contradictory readings at the same registered location."""
    conflicts = []
    for old in old_lines:
        if old['score'] < .92:
            continue
        for new in new_lines:
            if new['score'] < .92:
                continue
            oa, na = old['box'][2]*old['box'][3], new['box'][2]*new['box'][3]
            if intersects(old['box'],new['box']) / max(oa,na,1) < .45:
                continue
            a = re.sub(r'\W','',old['text']).lower()
            b = re.sub(r'\W','',new['text']).lower()
            if a != b and any(c.isdigit() for c in a+b):
                conflicts.append({'first':old['text'],'second':new['text']})
    return conflicts


def merge_regions(regions):
    """Nonoverlapping targets keep copy/rollback and provenance consistent."""
    merged=[]
    for original in regions:
        item=dict(original)
        while True:
            hit=next((r for r in merged if intersects(r['box'],item['box'])),None)
            if hit is None:
                break
            a,b=hit['box'],item['box']
            x,y=min(a[0],b[0]),min(a[1],b[1])
            item['box']=[x,y,max(a[0]+a[2],b[0]+b[2])-x,max(a[1]+a[3],b[1]+b[3])-y]
            if hit['reason']=='user-selected':item['reason']='user-selected'
            item['label']='Area yang saling bertumpang tindih'
            merged.remove(hit)
        merged.append(item)
    for i,item in enumerate(merged):item['id']=f'region-{i+1}'
    return merged


def recover(first_image, second_image, selected=None):
    started = time.perf_counter()
    result = inspect(first_image)
    first = decode_url(result['aligned'])
    base = decode_url(result['result'])
    second = second_image
    h, w = second.shape[:2]
    if max(h,w) > 2000:
        second = cv2.resize(second, None, fx=2000/max(h,w), fy=2000/max(h,w), interpolation=cv2.INTER_AREA)
    regions = result['regions']
    for b in selected or []:
        if len(b) != 4 or not all(isinstance(v,(int,float)) and np.isfinite(v) for v in b):
            raise ValueError('Koordinat area tidak valid.')
        x,y,bw,bh = b
        if min(x,y) < 0 or min(bw,bh) < .005 or x+bw > 1.001 or y+bh > 1.001:
            raise ValueError('Area harus berada di dalam halaman.')
        box = [int(x*first.shape[1]),int(y*first.shape[0]),max(1,int(bw*first.shape[1])),max(1,int(bh*first.shape[0]))]
        regions.append({'id':f'region-{len(regions)+1}','box':box,'reason':'user-selected',
                        'label':'Area yang kamu tandai','status':'unresolved','source':'photo-1'})
    if not regions:
        raise ValueError('Belum ada area pemulihan. Tandai bagian yang kurang jelas pada halaman terlebih dahulu.')
    regions=merge_regions(regions)
    warped, coverage, H, match = register(first, second)
    candidate_lines = read(warped)
    first_lines = result['before_lines']
    conflicts = check_identity(first_lines, candidate_lines)
    if conflicts:
        raise ValueError('Isi kedua foto bertentangan: '+ '; '.join(f"{c['first']} / {c['second']}" for c in conflicts[:3])+
                         '. Hasil tidak digabung. Pastikan halaman dan versi dokumennya sama; periksa juga bacaan OCR.')
    output = base.copy()
    source_mask = np.zeros(first.shape[:2], np.uint8)
    for region in regions:
        x,y,rw,rh = region['box']
        crop = warped[y:y+rh,x:x+rw]
        cover = coverage[y:y+rh,x:x+rw]
        old = first[y:y+rh,x:x+rw]
        reason = None
        supported_lines = [line for line in candidate_lines
                           if intersects(line['box'],region['box']) > line['box'][2]*line['box'][3]*.5 and line['score'] >= .85]
        colored = float(np.mean(obstruction(crop)>0)) if crop.size else 1
        if not cover.size or np.mean(cover>0) < .995:
            reason = 'Foto kedua belum mencakup seluruh area ini.'
        elif colored > .025:
            reason = 'Masih ada objek berwarna pada area ini; perlu tinjauan atau foto lain.'
        elif not supported_lines:
            reason = 'Belum ada teks yang cukup terbaca di area ini.'
        elif region['reason'] == 'possible-cover' and np.mean(obstruction(old)>0) <= colored+.02:
            reason = 'Penghalang belum terlihat berkurang.'
        elif region['reason'] in {'blur','low-ocr-score'} and metrics(crop)['sharpness'] < 45:
            reason = 'Detail foto kedua belum cukup tajam.'
        if reason:
            region['note'] = reason
            continue
        output[y:y+rh,x:x+rw] = crop
        source_mask[y:y+rh,x:x+rw] = 255
        region.update(status='recovered',source='photo-2',note='Piksel dari foto kedua; bacaan tetap perlu ditinjau.')
    final_lines = read(output, source_mask)
    # A copied area must still contain a readable line in the actual composite.
    for region in regions:
        if region['status'] == 'recovered' and not any(line['score'] >= .85 and intersects(line['box'],region['box']) for line in final_lines):
            x,y,rw,rh = region['box']
            output[y:y+rh,x:x+rw] = base[y:y+rh,x:x+rw]
            source_mask[y:y+rh,x:x+rw] = 0
            region.update(status='unresolved',source='photo-1',note='Pembacaan hasil gabungan gagal; salinan dibatalkan.')
    final_lines = read(output,source_mask)
    count = sum(r['status']=='recovered' for r in regions)
    result.update(result=data_url(output),after=metrics(output),status='review')
    result['trace'].extend([
        {'title':'Mencocokkan bukti baru','detail':f"{match['inliers']} titik cocok; galat median {match['median_error_px']} piksel."},
        {'title':'Memilih sumber per area','detail':f'{count} dari {len(regions)} area disalin dari foto kedua. Area tanpa bukti tetap ditandai.'},
        {'title':'Membaca ulang hasil gabungan','detail':f'{len(final_lines)} baris OCR. Tidak ada karakter yang dikarang.'}])
    pack(result,first,final_lines,regions,started)
    if all(r['status']=='recovered' for r in regions) and count:
        result['status']='review'
        result['instruction']='Area yang ditandai berhasil diambil dari foto kedua. Klik area untuk melihat sumbernya, lalu periksa teks dan angka penting.'
    if not result['page_detected']:
        result['status']='retake'
        result['instruction']='Batas halaman awal belum jelas. Ambil foto baru dengan empat sudut terlihat sebelum melanjutkan.'
    result.update(sources=[{'id':'photo-1','label':'Foto awal'},{'id':'photo-2','label':'Foto tambahan'}],
                  second_original=data_url(second), second_aligned=data_url(warped),
                  registration=match, second_to_page=H.tolist(), recovered_count=count)
    return result
