import unittest
from pathlib import Path
import numpy as np
import cv2
from app.vision import analyze,sample,text_perspective
from app.recovery import recover,decode_url,check_identity
from app.page_matches import find_matches


class PackageEvidenceTests(unittest.TestCase):
    def test_pdf_frame_does_not_disable_perspective(self):
        result=analyze(sample('perspective'),page_frame=True)
        self.assertEqual(result['geometry_source'],'detected-edges')
        self.assertIn('perspective',[i['kind'] for i in result['issues']])
        self.assertLess(decode_url(result['result']).shape[1],900)

    def test_matching_returns_views_but_not_blank(self):
        pairs=find_matches([sample('covered'),sample('second'),np.full((600,500,3),240,np.uint8)])['pairs']
        self.assertEqual([(p['first'],p['second']) for p in pairs],[(0,1)])

    def test_uncovered_prefix_is_not_numeric_conflict(self):
        a={'text':'Analysis at L3i','score':.99,'box':[0,0,200,20]}
        b={**a,'text':'Document Analysis at L3i'}
        self.assertEqual(check_identity([a],[b]),[])
        self.assertTrue(check_identity([{**a,'text':'INV-001'}],[{**b,'text':'INV-099'}]))

    def test_real_pdf_pair_recovers_text_and_keeps_remaining_obstruction(self):
        path=Path('output/pdf/scanpilot-close-camera-10-pages.pdf')
        if not path.exists():self.skipTest('Local public camera fixture is not distributed with the source archive.')
        from app.package import import_pdf
        pages=import_pdf(path.read_bytes())['pages']
        first,second=[decode_url(p['image']) for p in pages[:2]]
        self.assertIsNotNone(text_perspective(second))
        result=recover(first,second,first_page_frame=True)
        self.assertGreaterEqual(result['recovered_count'],1)
        self.assertTrue(any(r['status']=='unresolved' for r in result['regions']))
        self.assertTrue(any(l['source']=='photo-2' for l in result['lines']))
        self.assertEqual(result['status'],'retake')

if __name__=='__main__':unittest.main()
