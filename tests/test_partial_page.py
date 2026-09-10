import unittest
import cv2
import numpy as np
from app.page_geometry import partial_page_quad
from app.vision import sample, rectify


class PartialPageTests(unittest.TestCase):
    def test_clipped_corners_can_be_extended_from_visible_edges(self):
        photo = sample('perspective')[100:1100,80:860]
        points = partial_page_quad(photo)
        self.assertIsNotNone(points)
        expected = np.float32([[135,65],[840,135],[780,1130],[60,1035]])-[80,100]
        self.assertLess(float(np.max(np.linalg.norm(points-expected,axis=1))), 15)
        coverage=rectify(np.full(photo.shape,255,np.uint8),points)
        self.assertTrue(np.any(coverage==210))
        self.assertGreater(float(np.mean(coverage==255)), .9)

    def test_uniform_scene_has_no_supported_paper_edges(self):
        self.assertIsNone(partial_page_quad(np.full((600,400,3),240,np.uint8)))

    def test_only_two_visible_edges_are_insufficient(self):
        self.assertIsNone(partial_page_quad(sample('clear')[300:900,200:750]))
