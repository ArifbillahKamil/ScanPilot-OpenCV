"""Stateless, bounded PDF import/export. Original pages remain in the browser."""
from contextlib import closing
import hashlib
import io
import json
import threading

import cv2
import numpy as np
from PIL import Image
from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.vision import data_url

MAX_PAGES=20
MAX_PDF_BYTES=20*1024*1024
pdf_lock=threading.Lock()


def read_pdf(raw):
    from pypdf import PdfReader
    if len(raw)>MAX_PDF_BYTES:
        raise ValueError('PDF size must not exceed 20 MB.')
    if not raw.startswith(b'%PDF-'):
        raise ValueError('Choose a valid PDF file.')
    try:
        reader=PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise ValueError('Password-protected PDFs are not supported. Use an unlocked copy.')
        if not 1<=len(reader.pages)<=MAX_PAGES:
            raise ValueError('A package must contain 1 to 20 pages.')
        if reader.trailer['/Root'].get('/AcroForm'):
            raise ValueError('Interactive or signed PDFs are not supported. Use a non-interactive copy.')
        return reader
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('The PDF could not be read.') from error


def import_pdf(raw):
    import pypdfium2 as pdfium
    reader=read_pdf(raw)
    pages=[]
    # PDFium cannot run concurrently across threads, even for separate files.
    with pdf_lock:
        try:
            with pdfium.PdfDocument(raw) as document:
                for i,page_info in enumerate(reader.pages):
                    with closing(document[i]) as page:
                        width,height=page.get_size()
                        if min(width,height)<20 or max(width,height)>14400:
                            raise ValueError('A PDF page has unsupported dimensions.')
                        bitmap=page.render(scale=1600/max(width,height))
                        try:
                            rgb=bitmap.to_pil().convert('RGB')
                            image=cv2.cvtColor(np.asarray(rgb),cv2.COLOR_RGB2BGR)
                        finally:
                            bitmap.close()
                        with closing(page.get_textpage()) as textpage:
                            text=textpage.get_text_range()
                        # Conservative: image-bearing pages still receive visual inspection.
                        digital=len(text.strip())>=40 and len(page_info.images)==0
                        thumb=cv2.resize(image,(max(1,int(image.shape[1]*220/image.shape[0])),220))
                        pages.append({'number':i+1,'image':data_url(image),'thumbnail':data_url(thumb),
                                      'digital':digital,'text':text if digital else '',
                                      'width_pt':width,'height_pt':height})
        except ValueError:
            raise
        except Exception as error:
            raise ValueError('The PDF could not be rendered.') from error
    return {'pages':pages,'count':len(pages),'original_sha256':hashlib.sha256(raw).hexdigest()}


def export_package(manifest, original, images, report):
    from pypdf import PdfReader, PdfWriter, Transformation
    if not isinstance(manifest,list) or not 1<=len(manifest)<=MAX_PAGES:
        raise ValueError('A package must contain 1 to 20 pages.')
    reader=read_pdf(original) if original else None
    if reader and len(reader.pages)!=len(manifest):
        raise ValueError('The export must retain every original page.')
    writer=PdfWriter()
    for i,item in enumerate(manifest):
        if not isinstance(item,dict) or item.get('page')!=i:
            raise ValueError('Page order is invalid.')
        image_index=item.get('image')
        if image_index is None:
            if not reader:
                raise ValueError('A page is missing its image.')
            writer.append(reader,pages=[i])
            continue
        if type(image_index) is not int or not 0<=image_index<len(images):
            raise ValueError('A replacement page is missing.')
        stream=io.BytesIO()
        Image.fromarray(cv2.cvtColor(images[image_index],cv2.COLOR_BGR2RGB)).save(stream,format='PDF',resolution=150)
        raster=PdfReader(io.BytesIO(stream.getvalue())).pages[0]
        if reader:
            source=reader.pages[i]
            width,height=float(source.mediabox.width),float(source.mediabox.height)
            if source.rotation%180:
                width,height=height,width
            destination=writer.add_blank_page(width=width,height=height)
            rw,rh=float(raster.mediabox.width),float(raster.mediabox.height)
            scale=min(width/rw,height/rh)
            destination.merge_transformed_page(raster,Transformation().scale(scale).translate((width-rw*scale)/2,(height-rh*scale)/2))
        else:
            writer.add_page(raster)
    writer.add_metadata({'/Title':'ScanPilot document review','/Creator':'ScanPilot'})
    writer.add_attachment('scanpilot-review.json',json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'))
    result=io.BytesIO(); writer.write(result)
    return result.getvalue()


def install_routes(app, run_processing, load_image):
    @app.post('/api/package/import')
    def import_document(file: UploadFile):
        try:
            raw=file.file.read(MAX_PDF_BYTES+1)
            return run_processing(lambda: import_pdf(raw))
        finally:
            file.file.close()

    @app.post('/api/package/export')
    def export_document(manifest: str=Form(...), report: str=Form('{}'), original: UploadFile|None=File(None), images: list[UploadFile]=File(default=[])):
        try:
            if len(images)>MAX_PAGES or len(manifest)>10000 or len(report)>1_000_000:
                raise ValueError('The export request is too large.')
            plan=json.loads(manifest); review=json.loads(report)
            raw=original.file.read(MAX_PDF_BYTES+1) if original else None
            loaded=[]; pixels=0
            for file in images:
                image=load_image(file); pixels+=image.shape[0]*image.shape[1]
                if pixels>50_000_000: raise ValueError('Combined export images must not exceed 50 megapixels.')
                loaded.append(image)
            # Use the same bounded processing slot as OCR.
            result=run_processing(lambda: {'pdf':export_package(plan,raw,loaded,review)})
            return Response(result['pdf'],media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="scanpilot-package-review.pdf"'})
        except (ValueError,TypeError) as error:
            raise HTTPException(400,str(error)) from error
        finally:
            if original: original.file.close()
            for file in images: file.file.close()
