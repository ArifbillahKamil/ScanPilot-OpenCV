import time
import unittest
import numpy as np
from app.page_geometry import neutral_page_quad
from app.recovery import match_patch_lighting,pack


class ReleaseQualityTests(unittest.TestCase):
    def test_real_neutral_sheet_excludes_table(self):
        from pathlib import Path
        path=Path('tmp/pdfs/close-candidates/sample04_extra_picture00.jpg')
        if not path.exists():self.skipTest('Local camera fixture unavailable')
        from tools.benchmark_camera import load_photo
        from app.vision import page_quad,rectify
        image=load_photo(path)
        points=page_quad(image)
        self.assertIsNotNone(points)
        cropped=rectify(image,points)
        self.assertLess(cropped.shape[1],image.shape[1]*.5)
        self.assertGreater(cropped.shape[0],image.shape[0]*.8)

    def test_uniform_background_is_not_a_page(self):
        self.assertIsNone(neutral_page_quad(np.full((600,800,3),180,np.uint8)))

    def test_exposure_matching_preserves_new_ink(self):
        base=np.full((200,300,3),240,np.uint8)
        source=np.full_like(base,180)
        source[80:100,110:130]=0
        patch=match_patch_lighting(base,source,(100,60,60,60))
        self.assertLess(abs(int(patch[0,0,0])-240),3)
        self.assertEqual(int(patch[20,10,0]),0)
        self.assertEqual(int(base[80,110,0]),240)

    def test_uncertain_ocr_requires_review_not_automatic_retake(self):
        page=np.full((200,300,3),240,np.uint8)
        lines=[{'text':'uncertain','box':[10,10,80,20]}]
        regions=[{'reason':'low-ocr-score','status':'unresolved','box':[10,10,80,20]}]
        result=pack({'issues':[]},page,lines,regions,time.perf_counter())
        self.assertEqual(result['status'],'review')
        self.assertTrue(lines[0]['unresolved'])
        regions[0]['reason']='dark-cover'
        self.assertEqual(pack({'issues':[]},page,lines,regions,time.perf_counter())['status'],'retake')
