"""Real OCR and geometry integration tests; no model outputs are mocked."""
import io
import unittest

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app, processing_lock
from app.recovery import inspect, recover, decode_url
from app.vision import sample, encode


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.first = inspect(sample('covered'))
        cls.recovered = recover(sample('covered'),sample('second'))

    def test_covered_amount_is_not_invented(self):
        self.assertNotIn('271.000', self.first['text'])
        self.assertTrue(self.first['ocr_available'])
        self.assertEqual(self.first['status'],'retake')
        self.assertTrue(any(r['reason']=='possible-cover' for r in self.first['regions']))

    def test_second_photo_recovers_amount_with_source(self):
        result = self.recovered
        self.assertEqual(result['status'],'review')
        total = next(line for line in result['lines'] if '271.000' in line['text'])
        self.assertEqual(total['source'],'photo-2')
        self.assertGreater(result['registration']['inliers'],14)
        self.assertLess(result['registration']['median_error_px'],2)
        self.assertEqual(result['recovered_count'],1)
        # Only the selected region changes (allow JPEG export boundary ringing).
        before, after = decode_url(result['aligned']),decode_url(result['result'])
        self.assertLess(float(np.mean(np.abs(before[:600].astype(float)-after[:600]))),1.5)

    def test_repeated_obstruction_remains_unresolved(self):
        result = recover(sample('covered'),sample('covered-second'))
        self.assertEqual(result['recovered_count'],0)
        self.assertEqual(result['status'],'retake')
        self.assertNotIn('271.000',result['text'])

    def test_missing_target_coverage_remains_unresolved(self):
        result=recover(sample('covered'),sample('second')[:400])
        self.assertEqual(result['recovered_count'],0)
        self.assertIn('mencakup',result['regions'][0]['note'])

    def test_overlapping_targets_share_one_source_region(self):
        result=recover(sample('covered'),sample('second'),[[.48,.66,.49,.12]])
        self.assertEqual(len(result['regions']),1)
        self.assertEqual(result['recovered_count'],1)

    def test_same_template_different_document_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'bertentangan'):
            recover(sample('covered'),sample('different'))

    def test_visible_conflicting_amount_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'bertentangan'):
            recover(sample('clear'),sample('conflict'),[[.5,.65,.48,.15]])

    def test_no_shared_visual_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            recover(sample('covered'),np.full((700,600,3),240,np.uint8))

    def test_manual_area_handles_white_occlusion(self):
        first = sample('clear')
        # White paper covering is indistinguishable from an intentionally blank area.
        cv2.rectangle(first,(480,755),(795,829),(248,248,248),-1)
        result = recover(first,sample('second'),[[.48,.66,.49,.12]])
        self.assertIn('271.000',result['text'])
        self.assertEqual(result['recovered_count'],1)

    def test_api_recovery_and_pdf(self):
        response = self.client.post('/api/recover',files={
            'first':('first.jpg',encode(sample('covered')),'image/jpeg'),
            'second':('second.jpg',encode(sample('second')),'image/jpeg')})
        self.assertEqual(response.status_code,200,response.text[:200])
        self.assertEqual(response.json()['recovered_count'],1)
        pdf = self.client.post('/api/export/pdf',files={'file':('page.jpg',encode(sample('clear')),'image/jpeg')})
        self.assertEqual(pdf.status_code,200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_invalid_regions_and_busy_server(self):
        for areas in ['{}','[[0,0,2,1]]','[null]','[["bad",0,1,1]]']:
            response = self.client.post('/api/recover',data={'regions':areas},files={
                'first':('first.jpg',encode(sample('covered'))),
                'second':('second.jpg',encode(sample('second')))})
            self.assertIn(response.status_code,[400,422])
        processing_lock.acquire()
        try:
            response = self.client.post('/api/analyze',files={'file':('page.jpg',encode(sample('clear')))})
            self.assertEqual(response.status_code,429)
        finally:
            processing_lock.release()


if __name__=='__main__':
    unittest.main()
