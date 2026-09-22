import json
import tempfile
from pathlib import Path
from engine import Queue

with tempfile.TemporaryDirectory() as d:
    q = Queue(Path(d) / 'queue.db')
    job_id = q.submit('invoice:42', {'invoice': 42}, now=0)
    duplicate = q.submit('invoice:42', {'invoice': 42}, now=0)
    first = q.claim(now=0, lease=10)
    q.fail(first['id'], first['token'], 'temporary outage', now=1)
    retry = q.claim(now=3, lease=10)
    q.ack(retry['id'], retry['token'], now=4)
    print(json.dumps({'deduplicated': job_id == duplicate, 'job': q.get(job_id)}, indent=2))
    q.close()
