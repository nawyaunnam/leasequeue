"""Read-only local report dashboard. Run live.py --watch in another terminal."""
import argparse
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Engineering portfolio · live report</title><style>
*{box-sizing:border-box}body{margin:0;background:#101721;color:#ecf1f6;font:16px system-ui;padding:5vw;max-width:1250px;margin:auto}
header{border-bottom:1px solid #34404c;padding-bottom:24px}small{color:#68ddbf;letter-spacing:2px}h1{font-size:clamp(28px,5vw,52px);margin:12px 0}
.meta{color:#a4b1c0;line-height:1.8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:28px 0}
.card,details{background:#1a2533;border:1px solid #34404c;border-radius:12px;padding:20px}.value{font-size:28px;font-weight:650;margin-top:10px;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;font-size:13px}a{color:#68ddbf}summary{cursor:pointer;font-weight:600}#status{color:#ffd18a}footer{color:#a4b1c0;font-size:13px;margin-top:32px}
</style><header><small>NAWYA UNNAM / ENGINEERING LAB</small><h1 id="title">Live data report</h1><div id="status" role="status">Loading report…</div><div class="meta" id="meta"></div></header>
<main><div class="grid" id="cards"></div><details><summary>Workflow results</summary><pre id="results"></pre></details><details style="margin-top:16px"><summary>Source provenance</summary><pre id="sources"></pre></details></main>
<footer>Read-only localhost dashboard · refreshes every 5 seconds · feed collection runs separately. Source timestamps show actual freshness. No production-performance claims.</footer>
<script>
async function refresh(){try{let r=await fetch('/report',{cache:'no-store'});if(!r.ok)throw Error(await r.text());let d=await r.json();
document.getElementById('title').textContent=d.result.project||'Live data report';document.getElementById('status').textContent=d.mode;
document.getElementById('meta').textContent='Report generated: '+d.generated_at+' · '+d.sources.length+' public source(s)';
let root=document.getElementById('cards');root.replaceChildren();Object.entries(d.result).filter(([k,v])=>k!=='project'&&!k.endsWith('_ms')&&!k.includes('watermark')&&(typeof v==='number'||typeof v==='boolean')).slice(0,8).forEach(([k,v])=>{let card=document.createElement('div');card.className='card';let label=document.createElement('div');label.textContent=k.replaceAll('_',' ');let value=document.createElement('div');value.className='value';value.textContent=typeof v==='number'&&!Number.isInteger(v)?v.toFixed(4):v;card.append(label,value);root.append(card)});
document.getElementById('results').textContent=JSON.stringify(d.result,null,2);document.getElementById('sources').textContent=JSON.stringify(d.sources,null,2);
}catch(e){document.getElementById('status').textContent='Report unavailable: run live.py first. '+e.message}}refresh();setInterval(refresh,5000);
</script></html>"""

def serve(report,port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/': status,body,kind=200,HTML.encode(),'text/html; charset=utf-8'
            elif self.path=='/report':
                try:
                    body=report.read_bytes();json.loads(body);status,kind=200,'application/json'
                except (OSError,ValueError): status,body,kind=503,b'No valid report.json yet','text/plain'
            else: status,body,kind=404,b'Not found','text/plain'
            self.send_response(status);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Dashboard: http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=Path('report.json'));p.add_argument('--port',type=int,default=8090)
    args=p.parse_args();serve(args.report,args.port)
