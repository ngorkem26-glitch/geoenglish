import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContentTests(unittest.TestCase):
    def test_catalog(self):
        data = json.loads((ROOT / 'data/lessons-index.json').read_text(encoding='utf8'))
        self.assertIsInstance(data['lessons'], list)
        ids = [x['id'] for x in data['lessons']]
        self.assertEqual(len(ids), len(set(ids)))
        for x in data['lessons']:
            self.assertTrue(x['title'])
            self.assertTrue(x['created_at'])
            self.assertTrue(x['quiz'])
            for q in x['quiz']:
                self.assertGreaterEqual(q['correct_index'], 0)
                self.assertLess(q['correct_index'], len(q['options']))

    def test_curriculum(self):
        curriculum = json.loads((ROOT / 'data/curriculum.json').read_text(encoding='utf8'))
        self.assertGreater(len(curriculum['topics']), 0)


if __name__ == '__main__':
    unittest.main()
