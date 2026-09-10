import unittest
from app.recovery import expand_to_readable_lines, intersects


class PartialLineRecoveryTests(unittest.TestCase):
    def test_small_cover_expands_to_whole_supported_line(self):
        region={'id':'r1','box':[100,100,30,30],'reason':'possible-cover','status':'unresolved'}
        line={'box':[105,105,400,20],'score':.98}
        result=expand_to_readable_lines([region],[line],(600,800,3))[0]
        self.assertEqual(result['detected_box'],region['box'])
        self.assertEqual(intersects(result['box'],line['box']),400*20)
        self.assertEqual(region['box'],[100,100,30,30])

    def test_distant_or_uncertain_readings_do_not_expand_target(self):
        region={'id':'r1','box':[100,100,30,30],'reason':'possible-cover','status':'unresolved'}
        lines=[{'box':[100,200,400,20],'score':.99},{'box':[105,105,400,20],'score':.4}]
        self.assertEqual(expand_to_readable_lines([region],lines,(600,800,3))[0]['box'],region['box'])

    def test_expanded_overlapping_targets_are_merged(self):
        regions=[{'id':str(i),'box':[x,100,30,30],'reason':'possible-cover','status':'unresolved'} for i,x in enumerate([100,300])]
        lines=[{'box':[105,105,400,20],'score':.98}]
        self.assertEqual(len(expand_to_readable_lines(regions,lines,(600,800,3))),1)
