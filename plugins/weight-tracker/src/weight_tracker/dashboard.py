from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from .analytics import daily_dashboard
from .config import AppConfig
from .service import WeightService


HTML = """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Weight dashboard</title><style>
:root{font-family:Arial,sans-serif;color:#16302d;background:#f5fbfa}.wrap{max-width:1000px;margin:0 auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}.card{background:white;border:1px solid #d5e8e4;border-radius:12px;padding:16px}.label{font-size:12px;color:#52706b}.value{font-size:26px;font-weight:700;margin-top:6px}.chart{background:white;border:1px solid #d5e8e4;border-radius:12px;padding:12px}button{background:#0f766e;color:white;border:0;border-radius:8px;padding:10px 14px;cursor:pointer}.muted{color:#52706b;font-size:13px}.raw{fill:none;stroke:#0f766e;stroke-width:2.5}.avg{fill:none;stroke:#f59e0b;stroke-width:2.5;stroke-dasharray:6 4}.dot{fill:#0f766e;cursor:help}.grid{stroke:#d5e8e4}.axis{fill:#52706b;font-size:12px}.tip{position:fixed;display:none;background:#16302d;color:#fff;padding:8px 10px;border-radius:7px;font-size:12px;pointer-events:none}</style></head><body><main class='wrap'><div class='top'><div><h1>Weight dashboard</h1><div id='updated' class='muted'></div></div><button id='refresh'>Refresh</button></div><section class='cards'><div class='card'><div class='label'>Latest daily average</div><div id='latest' class='value'>—</div></div><div class='card'><div class='label'>Current BMI</div><div id='bmi' class='value'>—</div><div id='bmi-note' class='muted'></div></div><div class='card'><div class='label'>7-day average change</div><div id='change' class='value'>—</div><div id='change-note' class='muted'></div></div></section><section class='chart'><svg id='chart' viewBox='0 0 920 410' role='img' aria-label='Daily weight and seven-day average chart'></svg><p class='muted'>Solid line: daily average. Dashed line: 7-day rolling average. Hover a point for details.</p></section></main><div id='tip' class='tip'></div><script>
const $=s=>document.querySelector(s),svg=$('#chart'),tip=$('#tip'); const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function path(points,key,x,y){return points.filter(p=>p[key]!=null).map((p,i)=>`${i?'L':'M'}${x(p)},${y(p[key])}`).join(' ')}
function showTip(e,text){tip.textContent=text;tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';tip.style.display='block'} function hideTip(){tip.style.display='none'}
function render(d){const p=d.points,unit=d.unit;if(!p.length){svg.innerHTML='<text x="460" y="205" text-anchor="middle" class="axis">No records yet</text>';return}const W=920,H=410,m={l:60,r:24,t:22,b:55},iw=W-m.l-m.r,ih=H-m.t-m.b;const vals=p.flatMap(q=>[q.weight,q.rolling_7d].filter(Number.isFinite));let lo=Math.floor((Math.min(...vals)-.4)*2)/2,hi=Math.ceil((Math.max(...vals)+.4)*2)/2;if(lo===hi){lo-=.5;hi+=.5}const x=q=>m.l+(p.length===1?iw/2:p.indexOf(q)/(p.length-1)*iw),y=v=>m.t+(hi-v)/(hi-lo)*ih;let grid='';for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4,yy=y(v);grid+=`<line class="grid" x1="${m.l}" x2="${m.l+iw}" y1="${yy}" y2="${yy}"/><text class="axis" x="${m.l-9}" y="${yy+4}" text-anchor="end">${v.toFixed(1)}</text>`}const labels=p.map((q,i)=>i===0||i===p.length-1||p.length<8||i%Math.ceil(p.length/6)===0?`<text class="axis" x="${x(q)}" y="${H-24}" text-anchor="middle">${q.date.slice(5)}</text>`:'').join('');const dots=p.map(q=>`<circle class="dot" cx="${x(q)}" cy="${y(q.weight)}" r="5" data-tip="${esc(`${q.date} · ${q.weight.toFixed(2)} ${unit} · ${q.measurements} measurement${q.measurements===1?'':'s'}`)}"/>`).join('');svg.innerHTML=`${grid}<path class="raw" d="${path(p,'weight',x,y)}"/><path class="avg" d="${path(p,'rolling_7d',x,y)}"/>${dots}${labels}<text class="axis" x="${m.l+iw/2}" y="${H-5}" text-anchor="middle">Date</text><text class="axis" transform="translate(16 ${m.t+ih/2}) rotate(-90)" text-anchor="middle">Weight (${unit})</text>`;svg.querySelectorAll('.dot').forEach(n=>{n.onmousemove=e=>showTip(e,n.dataset.tip);n.onmouseleave=hideTip})}
async function load(){const r=await fetch('/api/dashboard',{cache:'no-store'});if(!r.ok)throw Error(await r.text());const d=await r.json();const unit=d.unit;$('#latest').textContent=d.latest?`${d.latest.weight.toFixed(2)} ${unit}`:'—';$('#bmi').textContent=d.bmi.value??'—';$('#bmi-note').textContent=d.bmi.category?`${d.bmi.category} · ${d.bmi.standard}`:'';$('#change').textContent=d.seven_day_change?`${d.seven_day_change.display>0?'+':''}${d.seven_day_change.display.toFixed(2)} ${unit}`:'—';$('#change-note').textContent=d.seven_day_change?`${d.seven_day_change.current_days} vs ${d.seven_day_change.previous_days} observed days`:'';$('#updated').textContent=`Read ${new Date().toLocaleString()}`;render(d)} $('#refresh').onclick=()=>load().catch(e=>alert(e.message));load().catch(e=>{svg.innerHTML=`<text x="460" y="205" text-anchor="middle" class="axis">${esc(e.message)}</text>`});
</script></body></html>"""


class DashboardServer:
    _instance: ClassVar["DashboardServer | None"] = None

    def __init__(self, config: AppConfig):
        self.config = config
        self.service = WeightService(config)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(HTML.encode("utf-8"))
                    return
                if self.path == "/api/dashboard":
                    try:
                        payload = daily_dashboard(owner.service.list_records(), owner.config.timezone, owner.config.height_cm, owner.config.bmi_standard, owner.config.display_weight_unit)
                        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception as exc:
                        self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, *_):
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @classmethod
    def start(cls, config: AppConfig) -> str:
        if cls._instance is None:
            cls._instance = cls(config)
        port = cls._instance.httpd.server_port
        return f"http://127.0.0.1:{port}/"
