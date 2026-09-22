"""Durable, single-host, at-least-once queue using fenced leases."""
import json
import sqlite3
import uuid

class Queue:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            available REAL NOT NULL, expires REAL, token TEXT, error TEXT)""")

    def close(self):
        self.db.close()

    def submit(self, key, payload, now):
        if not isinstance(key, str) or not key:
            raise ValueError('a nonempty idempotency key is required')
        body = json.dumps(payload, sort_keys=True, allow_nan=False)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT id,payload FROM jobs WHERE key=?', (key,)).fetchone()
            if row:
                if row['payload'] != body:
                    raise ValueError('idempotency key reused with different payload')
                job_id = row['id']
            else:
                job_id = self.db.execute('INSERT INTO jobs(key,payload,available) VALUES(?,?,?)',
                                         (key, body, now)).lastrowid
            self.db.execute('COMMIT')
            return job_id
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def claim(self, now, lease=30, max_attempts=3):
        if lease <= 0 or max_attempts < 1:
            raise ValueError('lease and attempt limit must be positive')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute("""UPDATE jobs SET state='dead',token=NULL
                WHERE attempts>=? AND ((state='running' AND expires<=?)
                OR state='pending')""", (max_attempts, now))
            row = self.db.execute("""SELECT * FROM jobs WHERE attempts<? AND
                ((state='pending' AND available<=?) OR (state='running' AND expires<=?))
                ORDER BY available,id LIMIT 1""", (max_attempts, now, now)).fetchone()
            if not row:
                self.db.execute('COMMIT')
                return None
            token = uuid.uuid4().hex
            self.db.execute("""UPDATE jobs SET state='running', attempts=attempts+1,
                token=?,expires=? WHERE id=?""", (token, now + lease, row['id']))
            result = self.get(row['id'])
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def ack(self, job_id, token, now):
        changed = self.db.execute("""UPDATE jobs SET state='done',token=NULL,expires=NULL
            WHERE id=? AND token=? AND state='running' AND expires>?""",
            (job_id, token, now)).rowcount
        if not changed:
            raise ValueError('stale or expired lease')

    def fail(self, job_id, token, error, now, max_attempts=3):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            job = self.get(job_id)
            if not job or job['token'] != token or job['state'] != 'running' or job['expires'] <= now:
                raise ValueError('stale or expired lease')
            state = 'dead' if job['attempts'] >= max_attempts else 'pending'
            self.db.execute("""UPDATE jobs SET state=?,available=?,token=NULL,
                expires=NULL,error=? WHERE id=?""",
                (state, now + min(2 ** job['attempts'], 3600), str(error), job_id))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def get(self, job_id):
        row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        return result
