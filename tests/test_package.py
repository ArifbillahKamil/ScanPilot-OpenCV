import io
import json
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject

from app.main import app
from app.package import import_pdf, export_package, read_pdf
from app.vision import sample, encode


def fixture_pdf():
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content=DecodedStreamObject();content.set_data(b'BT /F1 20 Tf 45 700 Td (DIGITAL ORIGINAL - KEEP THIS TEXT SELECTABLE) Tj 0 -45 Td /F1 12 Tf (Page one contains original vector text. ScanPilot should preserve it.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    for kind in ['shadow','covered']:
        stream=io.BytesIO();Image.fromarray(cv2.cvtColor(sample(kind,language='en'),cv2.COLOR_BGR2RGB)).save(stream,format='PDF',resolution=150)
        writer.append(PdfReader(io.BytesIO(stream.getvalue())))
    output=io.BytesIO();writer.write(output);return output.getvalue()


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=fixture_pdf();cls.client=TestClient(app)

    def test_import_mixed_pdf_renders_every_page_and_detects_native_text(self):
        result=import_pdf(self.raw)
        self.assertEqual(result['count'],3)
        self.assertEqual([p['digital'] for p in result['pages']],[True,False,False])
        self.assertIn('DIGITAL ORIGINAL',result['pages'][0]['text'])
        self.assertTrue(all(p['image'].startswith('data:image/jpeg;') for p in result['pages']))

    def test_export_preserves_native_text_order_and_original_unresolved_page(self):
        plan=[{'page':0,'image':None},{'page':1,'image':0},{'page':2,'image':None}]
        output=export_package(plan,self.raw,[sample('clear')],{'pages':[1,2,3]})
        reader=PdfReader(io.BytesIO(output));original=PdfReader(io.BytesIO(self.raw))
        self.assertEqual(len(reader.pages),3)
        self.assertEqual(reader.pages[0].extract_text(),original.pages[0].extract_text())
        self.assertEqual(reader.pages[2].get_contents().get_data(),original.pages[2].get_contents().get_data())
        self.assertIn('scanpilot-review.json',reader.attachments)
        self.assertAlmostEqual(float(reader.pages[1].mediabox.width),float(original.pages[1].mediabox.width))

    def test_invalid_encrypted_and_over_limit_pdf_rejected(self):
        with self.assertRaises(ValueError): read_pdf(b'not PDF')
        writer=PdfWriter();writer.add_blank_page(width=600,height=800);writer.encrypt('secret');out=io.BytesIO();writer.write(out)
        with self.assertRaises(ValueError): read_pdf(out.getvalue())
        writer=PdfWriter()
        for _ in range(21):writer.add_blank_page(width=600,height=800)
        out=io.BytesIO();writer.write(out)
        with self.assertRaises(ValueError):read_pdf(out.getvalue())

    def test_bad_export_order_or_missing_page_rejected(self):
        for plan in [[{'page':0,'image':None}],[{'page':1,'image':None}]*3]:
            with self.assertRaises(ValueError):export_package(plan,self.raw,[],{})

    def test_routes_import_export_and_photo_only_package(self):
        response=self.client.post('/api/package/import',files={'file':('sample.pdf',self.raw,'application/pdf')})
        self.assertEqual(response.status_code,200,response.text[:200])
        response=self.client.post('/api/package/export',data={'manifest':json.dumps([{'page':i,'image':None} for i in range(3)]),'report':'{}'},files={'original':('sample.pdf',self.raw,'application/pdf')})
        self.assertEqual(response.status_code,200,response.text[:200] if response.status_code!=200 else '')
        self.assertEqual(len(PdfReader(io.BytesIO(response.content)).pages),3)
        response=self.client.post('/api/package/export',data={'manifest':'[{"page":0,"image":0}]'},files={'images':('page.jpg',encode(sample('clear')),'image/jpeg')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(PdfReader(io.BytesIO(response.content)).pages),1)


if __name__=='__main__':
    unittest.main()
