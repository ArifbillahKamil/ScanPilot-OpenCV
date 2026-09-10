import unittest
from unittest.mock import patch

import cv2
import numpy as np

from app.vision import analyze, correct_lighting, sample, rotate_expanded, text_tilt
from app.recovery import decode_url


class DiagnosisTests(unittest.TestCase):
    def test_text_straightens_when_page_corners_are_unavailable(self):
        photo = rotate_expanded(sample('clear')[250:950,180:780], 11)
        with patch('app.vision.page_quad', return_value=None), patch('app.vision.partial_page_quad', return_value=None):
            result = analyze(photo)
        self.assertFalse(result['page_detected'])
        self.assertAlmostEqual(result['text_rotation_degrees'], -11, delta=1.5)
        self.assertLess(abs(text_tilt(decode_url(result['aligned']))), 1)
        self.assertIn('tilt', [issue['kind'] for issue in result['issues']])

    def test_blank_does_not_supply_a_rotation(self):
        self.assertIsNone(text_tilt(np.full((500,500,3),240,np.uint8)))

    def test_combined_blur_tilt_perspective_and_shadow(self):
        image = cv2.GaussianBlur(sample('perspective'), (21,21), 5)
        image = np.uint8(image * np.linspace(.45, 1, image.shape[1])[None,:,None])
        result = analyze(image)
        kinds = {issue['kind'] for issue in result['issues']}
        self.assertTrue({'blur','tilt','perspective','uneven-light'} <= kinds, (kinds, result['before']))
        self.assertEqual(result['status'], 'retake')
        self.assertLess(result['after']['uneven_light'], result['before']['uneven_light'])

    def test_colored_ink_survives_shadow_correction(self):
        page = np.full((700,500,3), 245, np.uint8)
        cv2.putText(page, 'BLUE INK', (50,350), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (180,65,25), 4)
        dark = np.uint8(page*np.linspace(.45,1,500)[None,:,None])
        result = correct_lighting(dark)
        ink = (page[:,:,0] > page[:,:,2]+50) & (page[:,:,2] < 50)
        self.assertGreater(np.mean(result[:,:,0][ink].astype(float)-result[:,:,2][ink]), 100)
        old_hue = cv2.cvtColor(dark,cv2.COLOR_BGR2HSV)[:,:,0][ink].astype(float)
        new_hue = cv2.cvtColor(result,cv2.COLOR_BGR2HSV)[:,:,0][ink].astype(float)
        self.assertLess(np.mean(np.abs(old_hue-new_hue)), 2)

    def test_clear_page_is_not_reported_as_tilted(self):
        result = analyze(sample('clear'))
        self.assertEqual(result['issues'], [])

    def test_shadow_result_keeps_three_distinct_channels(self):
        result = analyze(sample('shadow'))
        output = decode_url(result['result'])
        self.assertTrue(np.any(output[:,:,0] != output[:,:,1]))


if __name__ == '__main__':
    unittest.main()
