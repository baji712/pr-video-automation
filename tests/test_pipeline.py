import unittest
from video_pipeline import permitted, SIZE, FPS

class PipelineTests(unittest.TestCase):
    def test_license_allow_list(self):
        self.assertTrue(permitted('CC0'))
        self.assertTrue(permitted('Public Domain'))
        self.assertFalse(permitted('CC BY-SA 4.0'))
        self.assertFalse(permitted('non-public domain'))
    def test_vertical_frame(self):
        self.assertEqual(SIZE,(640,1138))
        self.assertEqual(FPS,15)

if __name__=='__main__':
    unittest.main()
