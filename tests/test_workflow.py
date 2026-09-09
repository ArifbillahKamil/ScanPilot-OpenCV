import io
import unittest

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app, MAX_BYTES
from app.vision import analyze, encode, sample


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_perspective_finds_page_and_removes_background(self):
        result = analyze(sample('perspective'))
        self.assertTrue(result['page_detected'])
        self.assertEqual(result['status'], 'review')
        self.assertNotEqual(result['original'], result['result'])
        self.assertFalse(result['ocr_available'])

    def test_light_correction_improves_measured_uniformity(self):
        result = analyze(sample('shadow'))
        self.assertEqual(result['status'], 'review')
        self.assertLess(result['after']['uneven_light'], result['before']['uneven_light'] * .5)
        self.assertGreaterEqual(result['after']['sharpness'], result['before']['sharpness'] * .8)

    def test_blur_requests_retake_then_clear_photo_can_be_reviewed(self):
        first = self.client.post('/api/analyze', files={'file':('blur.jpg',encode(sample('blur')),'image/jpeg')})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['status'], 'retake')
        self.assertEqual(first.json()['aligned'], first.json()['result'])
        second = self.client.post('/api/analyze', files={'file':('clear.jpg',encode(sample('clear')),'image/jpeg')})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['status'], 'review')

    def test_blank_is_not_accepted_as_clear_document(self):
        self.assertEqual(analyze(np.full((600,400,3),255,np.uint8))['status'], 'retake')

    def test_invalid_pdf_tiny_and_large_files_are_rejected(self):
        for body in [b'not an image', b'%PDF-1.4', encode(np.zeros((50,50,3),np.uint8))]:
            with self.subTest(body_length=len(body)):
                self.assertEqual(self.client.post('/api/analyze',files={'file':('x.jpg',body)}).status_code,400)
        self.assertEqual(self.client.post('/api/analyze',files={'file':('x.jpg',b'x'*(MAX_BYTES+1))}).status_code,413)

    def test_rgba_png_is_supported(self):
        image = Image.new('RGBA',(400,600),(255,255,255,255))
        buffer=io.BytesIO(); image.save(buffer,format='PNG')
        response=self.client.post('/api/analyze',files={'file':('page.png',buffer.getvalue(),'image/png')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'retake')

    def test_routes_and_unknown_sample(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertTrue(self.client.get('/api/health').json()['opencv'].startswith('5.'))
        self.assertEqual(self.client.get('/api/sample/unknown').status_code,404)


if __name__=='__main__':
    unittest.main()
