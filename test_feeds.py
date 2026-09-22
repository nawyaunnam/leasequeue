import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch
from feeds import atomic_json,fetch

class FeedTests(unittest.TestCase):
    def test_atomic_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'nested/report.json';atomic_json(p,{'ok':True})
            self.assertEqual(json.loads(p.read_text()),{'ok':True})
            self.assertFalse(p.with_suffix('.json.tmp').exists())
    def test_network_failure_is_not_synthetic_fallback(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as d, patch('feeds.urllib.request.urlopen',side_effect=urllib.error.URLError('offline')),patch('feeds.time.sleep'):
            with self.assertRaises(urllib.error.URLError):fetch('https://example.com/data',d)
    def test_nonfinite_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):atomic_json(Path(d)/'r.json',{'score':float('nan')})
