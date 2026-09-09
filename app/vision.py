"""Bounded, deterministic document quality workflow. No OCR claims."""
import base64
import time

import cv2
import numpy as np


def encode(image):
    ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise ValueError('Gambar tidak dapat disimpan.')
    return data.tobytes()


def data_url(image):
    return 'data:image/jpeg;base64,' + base64.b64encode(encode(image)).decode()


def page_quad(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
    return cv2.warpPerspective(image, matrix, (width, height))


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


def analyze(image):
    started = time.perf_counter()
    h, w = image.shape[:2]
    if min(h, w) < 200:
        raise ValueError('Gambar terlalu kecil. Gunakan foto minimal 200 × 200 piksel.')
    if max(h, w) > 1600:
        image = cv2.resize(image, None, fx=1600/max(h,w), fy=1600/max(h,w), interpolation=cv2.INTER_AREA)
    points = page_quad(image)
    page = rectify(image, points) if points is not None else image.copy()
    before = metrics(page)
    trace = [{'title': 'Mencari batas halaman', 'detail': 'Empat sudut ditemukan.' if points is not None else 'Batas halaman belum cukup jelas.'}]
    result = page.copy()
    reasons = []
    if points is None:
        reasons.append('Letakkan kertas di permukaan gelap dan pastikan empat sudut masuk foto.')
    else:
        trace.append({'title': 'Meluruskan perspektif', 'detail': 'Halaman dipetakan ulang dari empat sudut yang terdeteksi.'})
    if before['sharpness'] < 45:
        reasons.append('Tahan HP dengan stabil, ketuk teks untuk fokus, lalu ambil foto lagi.')
        trace.append({'title': 'Meminta bukti baru', 'detail': 'Detail teks terlalu lemah. Penajaman tidak dapat membuktikan karakter yang hilang.'})
    elif before['uneven_light'] > .16:
        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        background = cv2.GaussianBlur(cv2.dilate(gray, np.ones((35,35),np.uint8)), (0,0), 15)
        normalized = cv2.divide(gray, np.maximum(background, 1), scale=245)
        candidate = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        candidate_metrics = metrics(candidate)
        if candidate_metrics['uneven_light'] < before['uneven_light'] and candidate_metrics['sharpness'] >= before['sharpness'] * .8:
            result = candidate
            trace.append({'title': 'Meratakan pencahayaan', 'detail': 'Koreksi diterapkan karena variasi cahaya berkurang tanpa penurunan ketajaman besar.'})
        else:
            reasons.append('Geser dokumen ke cahaya yang lebih merata, lalu ambil foto lagi.')
            trace.append({'title': 'Menolak koreksi', 'detail': 'Kandidat tidak memperbaiki pengukuran secara memadai.'})
    after = metrics(result)
    if after['sharpness'] < 45 and not reasons:
        reasons.append('Hasil masih kurang tajam. Ambil ulang foto dengan fokus pada teks.')
    trace.append({'title': 'Memeriksa hasil', 'detail': 'Foto ulang diperlukan.' if reasons else 'Koreksi tersedia untuk ditinjau. Isi dokumen belum diverifikasi.'})
    return {
        'status': 'retake' if reasons else 'review',
        'instruction': ' '.join(reasons) if reasons else 'Bandingkan foto dan hasilnya. Periksa angka penting sebelum digunakan.',
        'page_detected': points is not None,
        'before': before, 'after': after, 'trace': trace,
        'original': data_url(image), 'aligned': data_url(page), 'result': data_url(result),
        'elapsed_ms': round((time.perf_counter()-started)*1000),
        'opencv': cv2.__version__, 'ocr_available': False,
    }


def sample(kind, amount='271.000', invoice_id='SP-DEMO-001'):
    """Generated fixture, not a photograph or benchmark result."""
    page = np.full((1000, 700, 3), 248, np.uint8)
    def put(value, xy, size=.65, thickness=1):
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
