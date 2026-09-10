import time
import unittest
import cv2
import numpy as np
from app.reading import read
from app.recovery import regions_for, pack


class ReadingPrecisionTests(unittest.TestCase):
    def test_short_upright_words_are_not_flipped(self):
        page=np.full((400,700,3),245,np.uint8)
        for y,text in [(90,'Modul'),(190,'Menu'),(290,'ERP Estimation Framework')]:
            cv2.putText(page,text,(40,y),cv2.FONT_HERSHEY_SIMPLEX,.9,(30,30,30),2,cv2.LINE_AA)
        lines=read(page)
        self.assertIn('Modul',[line['text'] for line in lines])
        self.assertIn('Menu',[line['text'] for line in lines])
        for line in lines:
            self.assertEqual(''.join(line['text'].split()),''.join(line['raw_text'].split()))

    def test_nearby_line_does_not_inherit_uncertainty(self):
        page=np.full((400,400,3),245,np.uint8)
        lines=[{'text':'weak','box':[40,80,100,20],'uncertain':True},
               {'text':'clear','box':[40,101,100,20],'uncertain':False}]
        regions=regions_for(page,lines,100)
        pack({},page,lines,regions,time.perf_counter())
        self.assertTrue(lines[0]['unresolved'])
        self.assertFalse(lines[1]['unresolved'])

    def test_object_entering_text_area_is_flagged_without_page_corners(self):
        page=np.full((600,400,3),245,np.uint8)
        cv2.rectangle(page,(0,250),(145,300),(65,110,180),-1)
        lines=[{'text':'line','box':[100,90,230,20],'uncertain':False},
               {'text':'line','box':[100,490,230,20],'uncertain':False}]
        regions=regions_for(page,lines,100,detect_cover=False)
        self.assertEqual(len(regions),1)
        self.assertEqual(regions[0]['reason'],'possible-cover')
        self.assertLess(regions[0]['box'][2],90)
