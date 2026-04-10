import unittest
import os
import json

class TestProjectStructure(unittest.TestCase):
    def test_triple_targets_exists(self):
        """triple_targets.json 파일이 존재하는지 확인"""
        self.assertTrue(os.path.exists("triple_targets.json"))

    def test_triple_targets_valid_json(self):
        """triple_targets.json 파일이 유효한 JSON인지 확인"""
        with open("triple_targets.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIsInstance(data, dict)

    def test_indicators_importable(self):
        """indicators.py 모듈이 임포트 가능한지 확인"""
        try:
            import indicators
        except ImportError:
            self.fail("indicators.py could not be imported")

if __name__ == "__main__":
    unittest.main()
