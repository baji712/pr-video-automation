import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clipper.shorts import check_rights,find_moments
class RightsAndCuts(unittest.TestCase):
 def test_reject_no_rights(self):
  with self.assertRaises(ValueError):check_rights({})
 def test_reject_unlicensed_music(self):
  with self.assertRaises(ValueError):check_rights({'rights_basis':'owned','ownership_confirmed':True,
    'commercial_use_allowed':True,'title':'t','creator':'c','source_url':'https://example.com'})
 def test_valid_cc_by(self):
  p=Path(__file__).resolve().parents[1]/'clipper'/'demo_rights.json'
  self.assertEqual(check_rights(json.loads(p.read_text()))['rights_basis'],'cc_by')
 def test_top_moment_first_non_overlapping(self):
  scores=[(i%12)+.1*i/80 for i in range(80)]
  moments=find_moments(scores,80,5)
  self.assertEqual(len(moments),5)
  self.assertEqual(moments[0]['motion_score'],max(x['motion_score'] for x in moments))
  for i,x in enumerate(moments):
   for y in moments[i+1:]:
    self.assertGreaterEqual(abs(x['start']-y['start']),x['duration']+.8-1e-6)
if __name__=='__main__':unittest.main()
