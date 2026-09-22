import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from engine import Queue

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'jobs.db'
        self.q = Queue(self.path)
    def tearDown(self):
        self.q.close()
        self.tmp.cleanup()
    def test_idempotency_and_conflict(self):
        a = self.q.submit('a', {'x': 1}, 0)
        self.assertEqual(a, self.q.submit('a', {'x': 1}, 0))
        with self.assertRaises(ValueError):
            self.q.submit('a', {'x': 2}, 0)
    def test_expired_worker_cannot_ack(self):
        self.q.submit('a', {}, 0)
        old = self.q.claim(0, lease=1)
        new = self.q.claim(1)
        with self.assertRaises(ValueError):
            self.q.ack(old['id'], old['token'], 1)
        self.q.ack(new['id'], new['token'], 2)
        self.assertEqual(self.q.get(new['id'])['state'], 'done')
    def test_retry_backoff_and_dead_letter(self):
        self.q.submit('a', {}, 0)
        job = self.q.claim(0)
        self.q.fail(job['id'], job['token'], 'failure', 1)
        self.assertIsNone(self.q.claim(2))
        job = self.q.claim(3)
        self.q.fail(job['id'], job['token'], 'failure', 4, max_attempts=2)
        self.assertEqual(self.q.get(job['id'])['state'], 'dead')
    def test_claims_are_exclusive(self):
        for i in range(12): self.q.submit(str(i), {}, 0)
        def claim(_):
            q = Queue(self.path)
            try: return q.claim(0)['id']
            finally: q.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(claim, range(12)))
        self.assertEqual(len(set(ids)), 12)
    def test_crash_exhaustion(self):
        self.q.submit('a', {}, 0)
        job = self.q.claim(0, lease=1, max_attempts=1)
        self.assertIsNone(self.q.claim(2, max_attempts=1))
        self.assertEqual(self.q.get(job['id'])['state'], 'dead')
