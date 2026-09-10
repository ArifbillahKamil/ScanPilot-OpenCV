"""Bounded, deterministic document quality workflow. No OCR claims."""
import base64
import time

import cv2
import numpy as np
from app.page_geometry import partial_page_quad


def encode(image):
    ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise ValueError('Gambar tidak dapat disimpan.')
    return data.tobytes()


def data_url(image):
    return 'data:image/jpeg;base64,' + base64.b64encode(encode(image)).decode()


def page_quad(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (5, 5), 0)
    contours = []
    # Soft focus and shadows weaken page edges; inspect a second sensitivity too.
    for low, high in [(40,120), (10,35)]:
        edges = cv2.Canny(smooth, low, high)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        found, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours.extend(found)
    # A bright page against a darker surface can remain separable without crisp edges.
    _, foreground = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    found, _ = cv2.findContours(foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours.extend(c for c in found if cv2.contourArea(c) < gray.size*.95)
    area = gray.size
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        polygon = cv2.approxPolyDP(contour, 0.025 * cv2.arcLength(contour, True), True)
        if len(polygon) == 4 and cv2.isContourConvex(polygon) and cv2.contourArea(polygon) > area * .23:
            points = polygon.reshape(4, 2).astype(np.float32)
            # Angle ordering avoids repeated corners from sum/difference ties.
            center = points.mean(axis=0)
            points = points[np.argsort(np.arctan2(points[:, 1]-center[1], points[:, 0]-center[0]))]
            points = np.roll(points, -np.argmin(points.sum(axis=1)), axis=0)
            if min(np.linalg.norm(points - np.roll(points, 1, axis=0), axis=1)) < 80:
                continue
            return points
    return None


def rectify(image, points):
    tl, tr, br, bl = points
    width = int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl)))
    height = int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr)))
    destination = np.float32([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]])
    matrix = cv2.getPerspectiveTransform(points, destination)
    return cv2.warpPerspective(image, matrix, (width, height), borderValue=(210,210,210))


def metrics(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 700 / max(gray.shape)
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    # Ignore document boundary: crisp paper edges must not hide blurred text.
    h, w = gray.shape
    inner = gray[max(1,int(h*.06)):int(h*.94), max(1,int(w*.06)):int(w*.94)]
    sharpness = float(cv2.Laplacian(inner, cv2.CV_64F).var())
    background = cv2.dilate(inner, np.ones((25, 25), np.uint8))
    low, high = np.percentile(background, [10, 90])
    uneven = float((high-low)/max(high, 1))
    return {'sharpness': round(sharpness, 1), 'uneven_light': round(uneven, 3)}


def geometry_metrics(points):
    if points is None:
        return None
    tl, tr, br, bl = points
    top, bottom = tr-tl, br-bl
    left, right = bl-tl, br-tr
    tilt = float(np.degrees(np.arctan2(top[1], top[0])))
    ratios = [abs(np.linalg.norm(a)-np.linalg.norm(b))/max(np.linalg.norm(a), np.linalg.norm(b))
              for a, b in [(top, bottom), (left, right)]]
    angles = [abs(float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))))
              for a,b in [(top,left),(top,right),(bottom,left),(bottom,right)]]
    return {'tilt_degrees': round(tilt, 1), 'perspective_distortion': round(float(max(ratios+angles)), 3)}


def correct_lighting(page):
    # Scale all channels equally: illumination correction must not erase ink color.
    value = page.max(axis=2)
    size = max(15, int(min(page.shape[:2])*.05) | 1)
    background = cv2.GaussianBlur(cv2.dilate(value, np.ones((size,size),np.uint8)), (0,0), size/2)
    gain = np.clip(245.0 / np.maximum(background, 1), .8, 2.8)
    return np.uint8(np.clip(page.astype(np.float32)*gain[:,:,None], 0, 255))


def text_tilt(image):
    from app.reading import read
    angles = []
    for line in read(image):
        p = np.asarray(line['polygon'])
        edge = p[1]-p[0]
        height = np.linalg.norm(p[3]-p[0])
        angle = float(np.degrees(np.arctan2(edge[1],edge[0])))
        if line['score'] >= .85 and np.linalg.norm(edge) > max(60, height*3) and abs(angle) < 30:
            angles.append(angle)
    if len(angles) < 5:
        return None
    median = float(np.median(angles))
    agreeing = [a for a in angles if abs(a-median) < 3]
    if len(agreeing) < max(5, len(angles)*.7):
        return None
    return round(float(np.median(agreeing)), 2)


def rotate_expanded(image, angle):
    h,w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w/2,h/2), angle, 1)
    c,s = abs(matrix[0,0]),abs(matrix[0,1])
    width,height = int(np.ceil(w*c+h*s)),int(np.ceil(h*c+w*s))
    matrix[:,2] += [(width-w)/2,(height-h)/2]
    return cv2.warpAffine(image,matrix,(width,height),borderValue=(68,68,68))


def analyze(image, page_frame=False):
    started = time.perf_counter()
    h, w = image.shape[:2]
    if min(h, w) < 200:
        raise ValueError('Gambar terlalu kecil. Gunakan foto minimal 200 × 200 piksel.')
    if max(h, w) > 1600:
        image = cv2.resize(image, None, fx=1600/max(h,w), fy=1600/max(h,w), interpolation=cv2.INTER_AREA)
    ih,iw=image.shape[:2]
    points = np.float32([[0,0],[iw-1,0],[iw-1,ih-1],[0,ih-1]]) if page_frame else page_quad(image)
    estimated = False
    if points is None:
        points = partial_page_quad(image)
        estimated = points is not None
    geometry = geometry_metrics(points)
    page = rectify(image, points) if points is not None and not page_frame else image.copy()
    text_angle = text_tilt(image) if points is None or page_frame else None
    if text_angle is not None and abs(text_angle) > 1.5:
        page = rotate_expanded(image, text_angle)
    before = metrics(page)
    trace = [{'title': 'Mencari batas halaman', 'detail': 'Empat sudut ditemukan.' if points is not None else 'Batas halaman belum cukup jelas.'}]
    result = page.copy()
    reasons = []
    issues = []
    if page_frame and text_angle is not None and abs(text_angle)>1.5:
        issues.append({'kind':'tilt','label':'Halaman miring','action':'Diperbaiki'})
        trace.append({'title':'Meluruskan arah teks','detail':'Rotasi mengikuti arah baris teks. Batas halaman dan perspektif belum dipastikan.'})
    if estimated:
        issues.append({'kind':'partial-page', 'label':'Sudut halaman diperkirakan dari tepi', 'action':'Perlu ditinjau'})
        reasons.append('Perspektif diluruskan dari tepi kertas. Area abu-abu berada di luar foto; periksa batas hasil.')
        trace[0]['detail'] = 'Empat tepi terlihat; sebagian sudut berada di luar foto.'
    if points is None:
        issues.append({'kind':'page-boundary', 'label':'Batas halaman belum jelas', 'action':'Perlu foto ulang'})
        reasons.append('Letakkan kertas di permukaan gelap dan pastikan empat sudut masuk foto.')
        if text_angle is not None and abs(text_angle) > 1.5:
            issues.append({'kind':'tilt', 'label':'Halaman miring', 'action':'Diperbaiki'})
            trace.append({'title':'Meluruskan arah teks', 'detail':'Rotasi mengikuti arah baris teks. Batas halaman dan perspektif belum dipastikan.'})
    else:
        trace.append({'title': 'Meluruskan perspektif', 'detail': 'Halaman dipetakan ulang dari empat sudut yang terdeteksi.'})
        if abs(geometry['tilt_degrees']) > 1.5:
            issues.append({'kind':'tilt', 'label':'Halaman miring', 'action':'Diperbaiki'})
        if geometry['perspective_distortion'] > .06:
            issues.append({'kind':'perspective', 'label':'Distorsi perspektif', 'action':'Diperbaiki'})
    if before['sharpness'] < 45:
        issues.append({'kind':'blur', 'label':'Kemungkinan blur / detail teks lemah', 'action':'Perlu foto ulang'})
        reasons.append('Tahan HP dengan stabil, ketuk teks untuk fokus, lalu ambil foto lagi.')
        trace.append({'title': 'Meminta bukti baru', 'detail': 'Detail teks terlalu lemah. Penajaman tidak dapat membuktikan karakter yang hilang.'})
    if before['uneven_light'] > .16:
        issue = {'kind':'uneven-light', 'label':'Bayangan / cahaya tidak merata', 'action':'Perlu ditinjau'}
        issues.append(issue)
        candidate = correct_lighting(page)
        candidate_metrics = metrics(candidate)
        if candidate_metrics['uneven_light'] < before['uneven_light'] and candidate_metrics['sharpness'] >= before['sharpness'] * .8:
            result = candidate
            issue['action'] = 'Diperbaiki'
            trace.append({'title': 'Meratakan pencahayaan', 'detail': 'Koreksi diterapkan karena variasi cahaya berkurang tanpa penurunan ketajaman besar.'})
        else:
            reasons.append('Geser dokumen ke cahaya yang lebih merata, lalu ambil foto lagi.')
            trace.append({'title': 'Menolak koreksi', 'detail': 'Kandidat tidak memperbaiki pengukuran secara memadai.'})
    after = metrics(result)
    if estimated:
        # Keep missing evidence visibly gray after lighting correction.
        coverage = rectify(np.full(image.shape,255,np.uint8), points)
        missing = np.min(coverage,axis=2) < 254
        result[missing] = 210
        page[missing] = 210
    if after['sharpness'] < 45 and not reasons:
        reasons.append('Hasil masih kurang tajam. Ambil ulang foto dengan fokus pada teks.')
    trace.append({'title': 'Memeriksa hasil', 'detail': 'Foto ulang diperlukan.' if reasons else 'Koreksi tersedia untuk ditinjau. Isi dokumen belum diverifikasi.'})
    return {
        'status': 'retake' if reasons else 'review',
        'instruction': ' '.join(reasons) if reasons else 'Bandingkan foto dan hasilnya. Periksa angka penting sebelum digunakan.',
        'page_detected': points is not None and not estimated,
        'page_estimated': estimated,
        'issues': issues, 'geometry': geometry, 'text_rotation_degrees': text_angle,
        'before': before, 'after': after, 'trace': trace,
        'original': data_url(image), 'aligned': data_url(page), 'result': data_url(result),
        'elapsed_ms': round((time.perf_counter()-started)*1000),
        'opencv': cv2.__version__, 'ocr_available': False,
    }


def sample(kind, amount='271.000', invoice_id='SP-DEMO-001', language='id'):
    """Generated fixture, not a photograph or benchmark result."""
    page = np.full((1000, 700, 3), 248, np.uint8)
    english = {
        'STUDIO CONTOH':'SAMPLE STUDIO',
        'Dokumen sintetis / Bukan tagihan':'Synthetic document / Not a real bill',
        'Pelanggan: Tim Administrasi Contoh':'Customer: Sample Administration Team',
        'BARANG                 QTY       JUMLAH':'ITEM                   QTY       AMOUNT',
        'Buku catatan             8       148.000':'Notebooks               8       148.000',
        'Map dokumen             12        78.000':'Document folders       12        78.000',
        'Pulpen hitam            10        45.000':'Black pens             10        45.000',
        'Seluruh nama dan transaksi adalah rekaan.':'All names and transactions are fictional.',
        'SCANPILOT / CONTOH UNTUK PENGEMBANGAN':'SCANPILOT / SYNTHETIC DEVELOPMENT SAMPLE',
    }
    def put(value, xy, size=.65, thickness=1):
        if language == 'en': value = english.get(value,value)
        cv2.putText(page, value, xy, cv2.FONT_HERSHEY_SIMPLEX, size, (35,39,35), thickness, cv2.LINE_AA)
    put('STUDIO CONTOH', (48,70), .7, 2)
    put('INVOICE', (48,150), 1.6, 3)
    put(invoice_id, (48,195))
    put('Dokumen sintetis / Bukan tagihan', (48,237), .55)
    cv2.line(page, (48,275), (652,275), (90,95,90), 1)
    put('Pelanggan: Tim Administrasi Contoh', (48,320), .6)
    put('08 September 2026', (48,360), .6)
    for y, text in [(450,'BARANG                 QTY       JUMLAH'),(505,'Buku catatan             8       148.000'),(560,'Map dokumen             12        78.000'),(615,'Pulpen hitam            10        45.000')]:
        put(text, (48,y), .62)
    cv2.line(page, (48,665), (652,665), (90,95,90), 1)
    put('TOTAL', (48,725), .9, 2)
    put('Rp '+amount, (385,725), .9, 2)
    put('Seluruh nama dan transaksi adalah rekaan.', (48,860), .55)
    put('SCANPILOT / CONTOH UNTUK PENGEMBANGAN', (48,925), .48)
    if kind == 'different':
        page[168:204,40:320] = 248
        put('SP-DEMO-099', (48,195))
    if kind == 'conflict':
        page[690:740,370:680] = 248
        put('Rp 971.000', (385,725), .9, 2)
    if kind in {'covered','covered-second'}:
        cv2.rectangle(page,(350,680),(665,754),(60,170,235),-1)
        cv2.line(page,(355,685),(660,685),(90,195,250),2)
    if kind in {'second','covered-second','different','conflict'}:
        # A closer second exposure retains identifiers and surrounding text.
        cropped = page[145:920,20:690]
        return cv2.copyMakeBorder(cropped,30,30,30,30,cv2.BORDER_CONSTANT,value=(70,74,80))
    if kind == 'shadow':
        illumination = np.linspace(.42, 1, 700)[None,:,None]
        page = np.uint8(page * illumination)
    if kind == 'blur':
        page = cv2.GaussianBlur(page, (31,31), 9)
    corners = np.float32([[135,65],[840,135],[780,1130],[60,1035]]) if kind == 'perspective' else np.float32([[130,75],[830,75],[830,1075],[130,1075]])
    transform = cv2.getPerspectiveTransform(np.float32([[0,0],[699,0],[699,999],[0,999]]),corners)
    return cv2.warpPerspective(page, transform, (950,1180), borderValue=(68,76,70))
