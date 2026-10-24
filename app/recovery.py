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


def dark_obstruction(image):
    """Long solid dark objects crossing text, rather than individual ink strokes."""
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);h,w=gray.shape
    mask=np.uint8(gray<65)*255
    vertical=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((max(25,int(h*.25)),9),np.uint8))
    horizontal=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((9,max(25,int(w*.25))),np.uint8))
    mask=cv2.bitwise_or(vertical,horizontal)
    out=np.zeros_like(mask)
    contours=[]
    for component in [vertical,horizontal]:
        contours.extend(cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0])
    for c in contours:
        x,y,bw,bh=cv2.boundingRect(c)
        if (bh>h*.3 and bw<w*.28 and bh>bw*3) or (bw>w*.3 and bh<h*.2 and bw>bh*4):
            cv2.drawContours(out,[c],-1,255,-1)
    return out


def intersects(a, b):
    x, y, w, h = a
    X, Y, W, H = b
    return max(0, min(x+w, X+W)-max(x, X)) * max(0, min(y+h, Y+H)-max(y, Y))


def regions_for(page, lines, sharpness, detect_cover=True):
    h, w = page.shape[:2]
    boxes = []
    dark=dark_obstruction(page)
    dark_contours,_=cv2.findContours(dark,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for c in dark_contours:
        x,y,bw,bh=cv2.boundingRect(c)
        boxes.append(([max(0,x-4),max(0,y-4),min(w,x+bw+4)-max(0,x-4),min(h,y+bh+4)-max(0,y-4)],'dark-cover'))
    mask = obstruction(page)
    # Large amounts of coloured print are common in posters and brochures.
    # Colour alone is insufficient evidence to demand a new photograph.
    if np.mean(mask>0)>.09 or np.any(dark):mask[:]=0
    if not detect_cover:
        # Without page corners, inspect only objects entering the observed text area.
        text_area=np.zeros_like(mask)
        if lines:
            x=min(l['box'][0] for l in lines); y=min(l['box'][1] for l in lines)
            right=max(l['box'][0]+l['box'][2] for l in lines)
            bottom=max(l['box'][1]+l['box'][3] for l in lines)
            text_area[y:bottom,x:right]=255
        mask=cv2.bitwise_and(mask,text_area)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv2.contourArea(contour) > h*w*(.002 if detect_cover else .0005):
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
                boxes.append(([max(0,x-2),max(0,y-2),min(w,x+bw+2)-max(0,x-2),
                               min(h,y+bh+2)-max(0,y-2)], 'low-ocr-score'))
    labels = {'dark-cover':'Kemungkinan tertutup benda gelap','possible-cover': 'Kemungkinan tertutup / objek berwarna',
              'blur': 'Detail teks terlalu lemah', 'low-ocr-score': 'Bacaan OCR meragukan'}
    return [{'id': f'region-{i+1}', 'box': b, 'reason': why, 'label': labels[why],
             'status': 'unresolved', 'source': 'photo-1'} for i, (b, why) in enumerate(boxes[:30])]


def match_patch_lighting(base, source, box):
    """Match exposure from surrounding bright pixels, never blend old ink into new text."""
    x,y,w,h=box
    margin=max(8,min(32,h//2))
    x0,y0=max(0,x-margin),max(0,y-margin)
    x1,y1=min(base.shape[1],x+w+margin),min(base.shape[0],y+h+margin)
    a=base[y0:y1,x0:x1];b=source[y0:y1,x0:x1]
    ring=np.ones(a.shape[:2],bool);ring[y-y0:y-y0+h,x-x0:x-x0+w]=False
    ring &= (a.min(axis=2)>100)&(b.min(axis=2)>100)
    crop=source[y:y+h,x:x+w]
    if ring.sum()<40:return crop
    ratios=np.median(a[ring].astype(float)/np.maximum(b[ring],1),axis=0)
    # Bound correction and preserve hue by applying one exposure multiplier.
    gain=float(np.clip(np.median(ratios),.75,1.35))
    return np.uint8(np.clip(crop.astype(float)*gain,0,255))


def pack(result, page, lines, regions, started):
    result.update(ocr_available=True, lines=lines, text=text_of(lines), regions=regions,
                  width=page.shape[1], height=page.shape[0],
                  elapsed_ms=round((time.perf_counter()-started)*1000),
                  planner='bounded-policy', sources=[{'id':'photo-1','label':'Foto awal'}])
    unresolved = [r for r in regions if r['status'] == 'unresolved']
    needs_photo=any(r['reason'] in {'possible-cover','dark-cover','blur','manual'} for r in unresolved)
    if unresolved and not needs_photo:
        result['status']='review' if not any(i['kind']=='blur' and i['action']=='Perlu foto ulang' for i in result.get('issues',[])) else 'retake'
        result['instruction']='Periksa bacaan dan batas halaman yang ditandai. Tambahkan foto lebih jelas hanya jika teks tidak dapat dibaca.'
    if needs_photo:
        result['status'] = 'retake'
        result['instruction'] = ('Ada bagian yang belum dapat diverifikasi. Singkirkan penghalang, ketuk teks untuk fokus, '
                                 'lalu tambahkan foto kedua dari halaman yang sama. Sertakan teks di sekitar area agar dapat dicocokkan.')
        if not any(r['reason'] in {'possible-cover','dark-cover'} for r in unresolved):
            result['instruction'] = ('Detail teks belum cukup jelas. Ketuk teks untuk fokus dan gunakan cahaya merata. '
                                     'Tambahkan foto kedua yang lebih tajam dengan teks di sekitar area tetap terlihat.')
    if not lines:
        result['status'] = 'retake'
        result['instruction'] = 'Belum ada teks yang terbaca. Ambil foto lebih tajam dengan keempat sudut halaman terlihat.'
    for line in lines:
        line['unresolved'] = any(intersects(line['box'], r['box']) > .25*line['box'][2]*line['box'][3] for r in unresolved)
    if result.get('page_estimated'):
        result['instruction'] = ('Perspektif diluruskan dari tepi kertas. Area abu-abu berada di luar foto; periksa batas hasil. '
                                 'Periksa bacaan OCR yang ditandai sebelum menggunakan dokumen.')
    return result


def inspect(image, page_frame=False):
    started = time.perf_counter()
    result = analyze(image, page_frame=page_frame)
    page = decode_url(result['aligned'])
    output = decode_url(result['result'])
    lines = read(output)
    result['before_lines'] = lines if result['aligned']==result['result'] else read(page)
    result['before_text'] = text_of(result['before_lines'])
    regions = regions_for(page, lines, result['before']['sharpness'], detect_cover=result['page_detected'])
    if any(r['reason'] == 'possible-cover' for r in regions):
        result['issues'].append({'kind':'possible-cover', 'label':'Kemungkinan tertutup / objek berwarna', 'action':'Perlu ditinjau'})
    if any(r['reason'] == 'dark-cover' for r in regions):
        result['issues'].append({'kind':'dark-cover','label':'Kemungkinan tertutup benda gelap','action':'Perlu ditinjau'})
    if any(r['reason'] == 'low-ocr-score' for r in regions):
        result['issues'].append({'kind':'low-ocr-score', 'label':'Bacaan OCR meragukan', 'action':'Perlu ditinjau'})
    result['trace'].append({'title':'Membaca teks dengan OCR lokal',
                            'detail':f'{len(lines)} baris terdeteksi. Skor model tidak membuktikan ketepatan isi.'})
    result['trace'].append({'title':'Memilih langkah berikutnya',
                            'detail':f'{len(regions)} area meminta bukti tambahan.' if regions else
                            'Tidak ada area mencurigakan yang terdeteksi. Tetap tinjau angka dan tandai area yang terlewat.'})
    return pack(result, page, lines, regions, started)


def register(first, second, features=None):
    sift = cv2.SIFT_create(nfeatures=4500)
    if features is None:
        k1, d1 = sift.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY), None)
        k2, d2 = sift.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_BGR2GRAY), None)
    else:
        (k1,d1),(k2,d2)=features
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
            # A newly uncovered prefix is not a conflicting number. Compare the
            # actual digit sequences, rather than rejecting any text containing a digit.
            if a != b and re.findall(r'\d+',a)!=re.findall(r'\d+',b) and re.search(r'\d',a) and re.search(r'\d',b):
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


def expand_to_readable_lines(regions, lines, shape):
    """Include whole supported lines when an obstruction covers only a few letters."""
    h,w=shape[:2]
    expanded=[]
    for original in regions:
        region=dict(original)
        if region['reason']=='possible-cover':
            target=region['box']
            related=[line['box'] for line in lines if line['score']>=.85 and
                     max(0,min(line['box'][1]+line['box'][3],target[1]+target[3])-max(line['box'][1],target[1])) > .25*line['box'][3]]
            if related:
                region['detected_box']=list(target)
                boxes=[target]+related
                x=max(0,min(b[0] for b in boxes)-3); y=max(0,min(b[1] for b in boxes)-3)
                right=min(w,max(b[0]+b[2] for b in boxes)+3)
                bottom=min(h,max(b[1]+b[3] for b in boxes)+3)
                region['box']=[x,y,right-x,bottom-y]
        expanded.append(region)
    return merge_regions(expanded)


def recover(first_image, second_image, selected=None, first_page_frame=False):
    started = time.perf_counter()
    result = inspect(first_image,page_frame=first_page_frame)
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
    # Split a long obstruction into text-sized targets. Other photographs may
    # uncover only some rows; requiring the whole pole to disappear loses them.
    split=[];unseen_dark=np.zeros(first.shape[:2],np.uint8)
    dark=dark_obstruction(first)
    for region in regions:
        if region['reason']!='dark-cover':split.append(region);continue
        supported=[]
        for line in candidate_lines:
            x,y,rw,rh=line['box']
            if line['score']<.88 or not intersects(line['box'],region['box']):continue
            oldmask=dark[y:y+rh,x:x+rw]
            if oldmask.size and np.mean(oldmask>0)>.06:
                supported.append({**region,'box':[x,y,rw,rh]})
        split.extend(supported or [region])
        if supported:
            x,y,rw,rh=region['box'];unseen_dark[y:y+rh,x:x+rw]=dark[y:y+rh,x:x+rw]
            for target in supported:
                x,y,rw,rh=target['box'];unseen_dark[y:y+rh,x:x+rw]=0
    regions=split
    regions=expand_to_readable_lines(regions,candidate_lines,first.shape)
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
        elif region['reason']=='dark-cover' and (np.mean(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)<65) >= np.mean(cv2.cvtColor(old,cv2.COLOR_BGR2GRAY)<65)-.06):
            reason = 'Penghalang belum terlihat berkurang.'
        elif colored > .025 and region['reason'] not in {'dark-cover','low-ocr-score'}:
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
        output[y:y+rh,x:x+rw] = match_patch_lighting(base,warped,(x,y,rw,rh))
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
    # Missing evidence outside newly readable rows must not silently disappear.
    for c in cv2.findContours(unseen_dark,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
        if cv2.contourArea(c)<first.shape[0]*first.shape[1]*.001:continue
        regions.append({'box':list(cv2.boundingRect(c)),'reason':'dark-cover','label':'Kemungkinan tertutup benda gelap','status':'unresolved','source':'photo-1','note':'Belum ada teks yang cukup terbaca di area ini.'})
    for i,region in enumerate(regions):region['id']=f'region-{i+1}'
    count = sum(r['status']=='recovered' for r in regions)
    result.update(result=data_url(output),after=metrics(output),status='review')
    for issue in result['issues']:
        matching=[r for r in regions if r['reason']==issue['kind']]
        if matching and all(r['status']=='recovered' for r in matching):issue['action']='Diperbaiki'
    result['trace'].extend([
        {'title':'Mencocokkan bukti baru','detail':f"{match['inliers']} titik cocok; galat median {match['median_error_px']} piksel."},
        {'title':'Memilih sumber per area','detail':f'{count} dari {len(regions)} area disalin dari foto kedua. Area tanpa bukti tetap ditandai.'},
        {'title':'Membaca ulang hasil gabungan','detail':f'{len(final_lines)} baris OCR. Tidak ada karakter yang dikarang.'}])
    pack(result,first,final_lines,regions,started)
    if all(r['status']=='recovered' for r in regions) and count:
        result['status']='review'
        result['instruction']='Area yang ditandai berhasil diambil dari foto kedua. Klik area untuk melihat sumbernya, lalu periksa teks dan angka penting.'
    if not count:
        notes=list(dict.fromkeys(r.get('note','') for r in regions if r.get('note')))
        result['instruction']='Foto kedua sudah diperiksa, tetapi belum ada area yang dapat digabung. '+ ' '.join(notes)
    result.update(sources=[{'id':'photo-1','label':'Foto awal'},{'id':'photo-2','label':'Foto tambahan'}],
                  second_original=data_url(second), second_aligned=data_url(warped),
                  registration=match, second_to_page=H.tolist(), recovered_count=count)
    return result
