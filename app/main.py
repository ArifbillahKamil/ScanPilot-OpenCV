import io
import json
import os
import threading
import warnings
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.vision import analyze, encode, sample
from app.recovery import inspect as inspect_document, recover
from app.limits import RequestPolicy

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 12 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 24_000_000
app = FastAPI(title='ScanPilot', version='0.2.0')
processing_lock = threading.Semaphore(1)
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
app.add_middleware(RequestPolicy)


@app.get('/')
def index():
    return FileResponse(ROOT/'static'/'index.html')


@app.get('/api/health')
def health():
    return {'opencv': cv2.__version__, 'ocr': True, 'mode': os.getenv('SCANPILOT_RUNTIME','local'),
            'planner':'bounded-policy', 'storage':'none', 'max_photos':2,'max_package_pages':20,'pdf':True}


@app.get('/api/sample/{kind}')
def example(kind: str, lang: str = 'id'):
    if kind not in {'perspective','shadow','blur','clear','covered','second','covered-second','different','conflict'}:
        raise HTTPException(404, 'Contoh tidak ditemukan.')
    return Response(encode(sample(kind,language='en' if lang=='en' else 'id')), media_type='image/jpeg', headers={'Cache-Control':'no-store'})


def load_image(file: UploadFile):
    try:
        raw = file.file.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, 'Ukuran maksimal 12 MB.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as loaded:
                if loaded.format not in {'JPEG','PNG','WEBP'}:
                    raise ValueError('Gunakan JPG, PNG, atau WebP. PDF dan HEIC belum didukung.')
                if loaded.width * loaded.height > 24_000_000:
                    raise ValueError('Resolusi maksimal 24 megapiksel.')
                rgb = ImageOps.exif_transpose(loaded).convert('RGB')
                image = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
        if min(image.shape[:2]) < 200:
            raise ValueError('Gambar terlalu kecil. Gunakan foto minimal 200 x 200 piksel.')
        return image
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise HTTPException(400, str(error) if isinstance(error, ValueError) else 'File tidak dapat dibaca sebagai gambar yang didukung.') from error
    finally:
        file.file.close()


def run_processing(action):
    if not processing_lock.acquire(blocking=False):
        raise HTTPException(429, 'ScanPilot sedang memproses foto lain. Coba lagi beberapa saat.')
    try:
        result = action()
        result['runtime'] = os.getenv('SCANPILOT_RUNTIME','local')
        return result
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    finally:
        processing_lock.release()


@app.post('/api/analyze')
def inspect(file: UploadFile, page_frame: bool = Form(False)):
    image = load_image(file)
    return run_processing(lambda: inspect_document(image, page_frame=page_frame))


@app.post('/api/recover')
def recover_document(first: UploadFile, second: UploadFile, regions: str = Form('[]'), first_page_frame: bool=Form(False)):
    try:
        selected = json.loads(regions)
        if not isinstance(selected, list) or len(selected) > 10 or any(not isinstance(b,list) for b in selected):
            raise ValueError('Maksimal sepuluh area tambahan.')
        first_image, second_image = load_image(first), load_image(second)
        return run_processing(lambda: recover(first_image,second_image,selected,first_page_frame=first_page_frame))
    except (ValueError, TypeError) as error:
        raise HTTPException(400, 'Format area tidak valid.') from error
    finally:
        first.file.close()
        second.file.close()


@app.post('/api/export/pdf')
def export_pdf(file: UploadFile):
    image = load_image(file)
    stream = io.BytesIO()
    Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB)).save(stream,format='PDF',resolution=150)
    return Response(stream.getvalue(),media_type='application/pdf',
                    headers={'Content-Disposition':'attachment; filename="scanpilot-review.pdf"','Cache-Control':'no-store'})


@app.middleware('http')
async def response_policy(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


from app.package import install_routes
install_routes(app,run_processing,load_image)
