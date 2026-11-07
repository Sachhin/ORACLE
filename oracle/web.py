"""Local browser dashboard for ORACLE research runs.

The server binds to loopback by default. It launches the same installed CLI used
by terminal users and reads completed research records from the shared SQLite DB.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .storage import ResearchStore

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ORACLE · Scientific Research</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#141c30;--line:#283550;--muted:#9eacc4;--accent:#8bb8ff;--good:#70d6a1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#edf3ff;font:15px/1.5 system-ui, sans-serif}
header{padding:22px max(18px,calc((100% - 1120px)/2));border-bottom:1px solid var(--line);background:#10182a}
h1{margin:0;font-size:25px}header p{margin:4px 0 0;color:var(--muted)}
main{max-width:1120px;margin:24px auto;padding:0 16px;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:18px}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;min-width:0}
h2{font-size:18px;margin:0 0 14px}label{display:block;color:#cbd7ea;margin:12px 0 5px}
input,select,textarea{width:100%;padding:11px;border:1px solid #344563;border-radius:8px;background:#0d1526;color:#fff;font:inherit}
textarea{min-height:92px;resize:vertical}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.check{display:flex;gap:9px;align-items:center;margin:12px 0;color:#cbd7ea}.check input{width:auto}
button{border:0;border-radius:9px;background:var(--accent);color:#071326;padding:11px 17px;font-weight:700;cursor:pointer}
button:disabled{opacity:.5;cursor:wait}.muted{color:var(--muted)}.status{padding:10px;border-radius:8px;background:#0d1526;margin-top:12px;white-space:pre-wrap}
.item{padding:12px 0;border-bottom:1px solid var(--line);cursor:pointer}.item:last-child{border:0}
.item strong{display:block}.pill{font-size:12px;color:var(--good)}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto;background:#0b1323;padding:12px;border-radius:8px;color:#d2def1}
@media(max-width:760px){main{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
</style></head><body>
<header><h1>ORACLE <span style="color:#8bb8ff">2.0</span></h1><p>Scientific research and discovery workspace · local instance</p></header>
<main>
<section><h2>Start a research mission</h2>
<form id="mission">
<label>Research question</label><textarea id="question" required maxlength="2000" placeholder="Enter a scientific question…"></textarea>
<div class="grid"><div><label>Research mode</label><select id="mode"><option value="both">Deep research + discovery</option><option value="deep_research">Deep research</option><option value="autonomous_discovery">Autonomous discovery</option></select></div>
<div><label>Domain</label><select id="domain"><option value="auto">Automatic</option><option value="biology_medicine">Biology & medicine</option><option value="physics_astronomy">Physics & astronomy</option><option value="chemistry_materials">Chemistry & materials</option><option value="computer_science_ai">Computer science & AI</option><option value="earth_environment">Earth & environment</option><option value="mathematics_statistics">Mathematics & statistics</option><option value="social_behavioral">Social & behavioural science</option><option value="engineering">Engineering</option><option value="general_science">General science</option></select></div></div>
<div class="grid"><div><label>Research cycles (1–8)</label><input id="cycles" type="number" min="1" max="8" value="3"></div>
<div><label>Literature records (1–50)</label><input id="limit" type="number" min="1" max="50" value="20"></div></div>
<div class="status">Runs with ORACLE’s built-in deterministic research workflow. No Gemini API key or paid AI API is used.</div>
<label class="check"><input id="fulltext" type="checkbox" checked> Retrieve eligible open-access full text</label>
<label class="check"><input id="citations" type="checkbox" checked> Expand citation network</label>
<label class="check"><input id="geoDiscover" type="checkbox"> Discover GEO supplementary files (no downloads)</label>
<label class="check"><input id="geoAnalyze" type="checkbox"> Download and analyze supported GEO matrices (uses bandwidth and disk space)</label>
<button id="start" type="submit">Start research</button>
<div id="status" class="status" role="status">Ready. Research runs may take several minutes while public scientific literature is retrieved.</div>
</form><h2 style="margin-top:22px">Selected run</h2><div id="detail" class="muted">Select a run from the history panel to inspect its summary.</div></section>
<section><h2>Research history</h2><button id="refresh" type="button">Refresh runs</button><div id="runs" class="muted" style="margin-top:12px">Loading…</div></section>
</main>
<script>
const $=id=>document.getElementById(id);let activeJob=null;
async function api(path,opts){const r=await fetch(path,opts);const j=await r.json();if(!r.ok)throw Error(j.error||r.statusText);return j}
function showStatus(s){$('status').textContent=s}
async function refresh(){try{const d=await api('/api/runs');$('runs').replaceChildren();if(!d.runs.length){$('runs').textContent='No saved research runs yet.';return}
for(const r of d.runs){const el=document.createElement('div');el.className='item';const b=document.createElement('strong');b.textContent=r.question;const m=document.createElement('span');m.className='muted';m.textContent=r.status+' · '+r.run_id+' · '+r.updated_at;el.append(b,m);el.onclick=()=>selectRun(r.run_id);$('runs').append(el)}}catch(e){$('runs').textContent=e.message}}
async function selectRun(id){try{const d=await api('/api/runs/'+encodeURIComponent(id));const r=d.run;$('detail').replaceChildren();const h=document.createElement('h3');h.textContent=r.question;const p=document.createElement('p');p.textContent='Status: '+r.status+' · Cycles: '+r.current_cycle+'/'+r.max_cycles+' · Sources: '+r.sources.length+' · Evidence: '+r.evidence.length+' · Claims: '+r.claims.length+' · Hypotheses: '+r.hypotheses.length;const pre=document.createElement('pre');pre.textContent=(r.findings||[]).join('\n\n')||'No findings recorded.';$('detail').append(h,p,pre)}catch(e){showStatus(e.message)}}
$('mission').onsubmit=async e=>{e.preventDefault();$('start').disabled=true;showStatus('Submitting research mission…');
try{const payload={question:$('question').value,mode:$('mode').value,domain:$('domain').value,cycles:Number($('cycles').value),limit:Number($('limit').value),full_text:$('fulltext').checked,citations:$('citations').checked,geo_discover:$('geoDiscover').checked,geo_analyze:$('geoAnalyze').checked};
const d=await api('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});activeJob=d.job_id;showStatus('Run started: '+activeJob);poll()}catch(err){showStatus('Could not start: '+err.message);$('start').disabled=false}};
async function poll(){if(!activeJob)return;try{const d=await api('/api/jobs/'+activeJob);showStatus('Job '+d.status+(d.run_id?' · Run '+d.run_id:'')+(d.error?'\n'+d.error:''));if(d.status==='completed'){activeJob=null;$('start').disabled=false;await refresh();if(d.run_id)await selectRun(d.run_id);return}if(d.status==='failed'){activeJob=null;$('start').disabled=false;return}setTimeout(poll,3000)}catch(e){showStatus(e.message);activeJob=null;$('start').disabled=false}}
$('refresh').onclick=refresh;refresh();
</script></body></html>"""


class OracleDashboardHandler(BaseHTTPRequestHandler):
    server_version = "ORACLE-Dashboard/1.0"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/runs":
            try:
                db_path = Path(os.environ.get("ORACLE_DB", "data/oracle.sqlite3"))
                store = ResearchStore(db_path)
                with store._connect() as db:
                    rows = db.execute(
                        "SELECT run_id,status,question,updated_at FROM runs ORDER BY updated_at DESC LIMIT 100"
                    ).fetchall()
                self._json(200, {"runs": [dict(row) for row in rows]})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if path.startswith("/api/runs/"):
            run_id = path.rsplit("/", 1)[-1]
            try:
                run = ResearchStore(os.environ.get("ORACLE_DB", "data/oracle.sqlite3")).load_run(run_id)
                if run is None:
                    self._json(404, {"error": "Research run not found"})
                else:
                    self._json(200, {"run": run.to_dict()})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self._json(404, {"error": "Job not found; jobs are held in memory until the server restarts"})
                return
            process = job["process"]
            status = "running" if process.poll() is None else ("completed" if process.returncode == 0 else "failed")
            run_id = ""
            error = ""
            if status == "completed":
                try:
                    data = json.loads(Path(job["output"]).read_text(encoding="utf-8"))
                    run_id = data.get("run_id", "")
                except Exception as exc:
                    status, error = "failed", f"Could not read research result: {exc}"
            elif status == "failed":
                try:
                    error = Path(job["log"]).read_text(encoding="utf-8")[-5000:]
                except OSError:
                    error = "Research process exited unsuccessfully."
            self._json(200, {"job_id": job_id, "status": status, "run_id": run_id, "error": error})
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self._json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 12000:
                raise ValueError("Invalid request size.")
            payload = json.loads(self.rfile.read(length))
            question = str(payload.get("question", "")).strip()
            if not question or len(question) > 2000:
                raise ValueError("Enter a research question up to 2,000 characters.")
            mode = payload.get("mode", "both")
            if mode not in {"both", "deep_research", "autonomous_discovery"}:
                raise ValueError("Invalid research mode.")
            domain = payload.get("domain", "auto")
            allowed_domains = {"auto", "biology_medicine", "physics_astronomy", "chemistry_materials",
                "computer_science_ai", "earth_environment", "mathematics_statistics",
                "social_behavioral", "engineering", "general_science"}
            if domain not in allowed_domains:
                raise ValueError("Invalid research domain.")
            cycles = int(payload.get("cycles", 3))
            limit = int(payload.get("limit", 20))
            if not 1 <= cycles <= 8 or not 1 <= limit <= 50:
                raise ValueError("Cycles must be 1–8 and literature limit 1–50.")
            root = Path(os.environ.get("ORACLE_WORKDIR", ".")).resolve()
            job_dir = root / ".oracle-web" / "jobs"
            job_dir.mkdir(parents=True, exist_ok=True)
            job_id = uuid.uuid4().hex
            output, log = job_dir / f"{job_id}.json", job_dir / f"{job_id}.log"
            literature_provider = "biology" if domain == "biology_medicine" else "both"
            command = [sys.executable, "-m", "oracle", question, "--mode", mode,
                "--domain", domain, "--cycles", str(cycles), "--limit", str(limit),
                "--agent-provider", "deterministic", "--research-literature", "--provider", literature_provider,
                "--db", os.environ.get("ORACLE_DB", "data/oracle.sqlite3"), "--json"]
            if payload.get("full_text"):
                command.append("--full-text")
            if payload.get("citations"):
                command.extend(["--citation-network", "--incoming-citations"])
            if payload.get("geo_discover"):
                command.append("--discover-geo-files")
            if payload.get("geo_analyze"):
                command.append("--analyze-geo-files")
            with log.open("w", encoding="utf-8") as handle:
                process = subprocess.Popen(command, cwd=root, stdout=output.open("w", encoding="utf-8"),
                    stderr=handle, env=os.environ.copy())
            with JOBS_LOCK:
                JOBS[job_id] = {"process": process, "output": str(output), "log": str(log)}
            self._json(202, {"job_id": job_id, "status": "running"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        # Keep normal request logs quiet; startup prints the local URL.
        return


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Start the ORACLE local browser dashboard.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind address. Loopback is safest; do not expose publicly without authentication.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("The dashboard is unauthenticated; bind only to loopback.")
    server = ThreadingHTTPServer((args.host, args.port), OracleDashboardHandler)
    print(f"ORACLE dashboard: http://127.0.0.1:{args.port}")
    print("Keep this terminal running. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ORACLE dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
