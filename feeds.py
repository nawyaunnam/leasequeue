"""Public JSON feeds with bounded retries, verified TLS and ETag caching."""
import argparse
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

def atomic_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,indent=2,allow_nan=False))
    temp.replace(path)

def fetch(url,cache_dir='.cache'):
    cache=Path(cache_dir)/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    prior=json.loads(cache.read_text()) if cache.exists() else None
    headers={'User-Agent':'nawyaunnam-engineering-portfolio/1.0','Accept':'application/json'}
    if prior and prior.get('etag'): headers['If-None-Match']=prior['etag']
    # On some macOS Python installations the bundled CA file has not been installed.
    # Use the OS CA bundle when needed; certificate verification remains enabled.
    paths=ssl.get_default_verify_paths()
    cafile=paths.cafile
    if cafile is None and Path('/etc/ssl/cert.pem').exists(): cafile='/etc/ssl/cert.pem'
    context=ssl.create_default_context(cafile=cafile)
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(request,timeout=30,context=context) as response:
                body=response.read(20_000_001)
                if len(body)>20_000_000: raise ValueError('feed exceeds 20 MB limit')
                payload=json.loads(body)
                result={'url':url,'fetched_at':datetime.now(timezone.utc).isoformat(),
                        'etag':response.headers.get('ETag'),'poll_interval':max(60,int(response.headers.get('X-Poll-Interval','60'))),
                        'payload':payload}
                atomic_json(cache,result)
                return result
        except urllib.error.HTTPError as error:
            if error.code==304 and prior:
                return dict(prior,checked_at=datetime.now(timezone.utc).isoformat(),not_modified=True)
            if error.code not in (429,500,502,503,504) or attempt==2: raise
            delay=error.headers.get('Retry-After','')
            time.sleep(min(int(delay) if delay.isdigit() else 2**attempt,60))
        except (urllib.error.URLError,TimeoutError):
            if attempt==2: raise
            time.sleep(2**attempt)
    raise RuntimeError('feed retries exhausted')

def run(acquire,analyze):
    parser=argparse.ArgumentParser(description='Live public-data workflow; no API keys required.')
    parser.add_argument('--replay',type=Path,help='Analyze a previously captured snapshot without network access')
    parser.add_argument('--snapshot',type=Path,default=Path('snapshot.json'))
    parser.add_argument('--output',type=Path,default=Path('report.json'))
    parser.add_argument('--watch',type=int,default=0,help='Refresh interval in seconds (minimum 60); Ctrl+C stops')
    args=parser.parse_args()
    if args.watch and args.watch<60: parser.error('--watch must be at least 60 seconds')
    if args.watch and args.replay: parser.error('replay cannot be combined with watch')
    while True:
        snapshot=json.loads(args.replay.read_text()) if args.replay else acquire()
        if not args.replay: atomic_json(args.snapshot,snapshot)
        result=analyze(snapshot)
        report={'mode':'snapshot replay' if args.replay else 'live fetch',
                'generated_at':datetime.now(timezone.utc).isoformat(),
                'sources':[{k:s[k] for k in ('url','fetched_at') if k in s} for s in snapshot['sources']],
                'result':result}
        atomic_json(args.output,report)
        print(json.dumps(report,indent=2))
        if not args.watch: break
        time.sleep(max(args.watch,max(s.get('poll_interval',60) for s in snapshot['sources'])))
