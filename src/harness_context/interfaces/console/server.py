from __future__ import annotations

import json
import secrets
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class _ConsoleHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, address, handler, runtime):
        self.runtime = runtime
        self.csrf_token = secrets.token_urlsafe(32)
        super().__init__(address, handler)


class _ConsoleHTTPServerV6(_ConsoleHTTPServer):
    address_family = socket.AF_INET6


class _ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "CTXORAConsole/1"

    def do_GET(self) -> None:
        request = urlparse(self.path)
        if request.path == "/":
            self._send(
                HTTPStatus.OK,
                _CONSOLE_HTML.encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if request.path == "/api/snapshot":
            self._send_json(HTTPStatus.OK, self.server.runtime.health_report())
            return
        if request.path == "/api/actions":
            runtime = self.server.runtime
            actions = runtime.container.operations.available_actions() if runtime.container else ()
            self._send_json(HTTPStatus.OK, {
                "schema_version": "ctxora.console-actions.v1",
                "actions": list(actions),
                "csrf_token": self.server.csrf_token,
            })
            return
        if request.path == "/api/events":
            try:
                self._send_json(HTTPStatus.OK, self._events(request.query))
            except ValueError as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        if request.path == "/events":
            try:
                payload = _json_bytes(self._events(request.query)).decode("utf-8")
            except ValueError as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            body = f"retry: 3000\nevent: events\ndata: {payload}\n\n".encode()
            self._send(HTTPStatus.OK, body, "text/event-stream; charset=utf-8")
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        request = urlparse(self.path)
        if request.path not in {"/api/actions/plan", "/api/actions/execute"}:
            self._method_not_allowed()
            return
        if not secrets.compare_digest(
            self.headers.get("X-CTXORA-CSRF", ""), self.server.csrf_token
        ):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "invalid CSRF token"})
            return
        try:
            payload = self._read_json()
            runtime = self.server.runtime
            if runtime.container is None:
                raise RuntimeError("console runtime is not ready")
            if request.path == "/api/actions/plan":
                result = runtime.container.operations.plan_action(
                    runtime.config.workspace_id,
                    str(payload.get("action", "")),
                    payload.get("parameters", {}),
                ).to_dict()
            else:
                result = runtime.container.operations.execute_action(
                    runtime.config.workspace_id,
                    str(payload.get("plan_digest", "")),
                    confirmed=payload.get("confirm") is True,
                ).to_dict()
        except (TypeError, ValueError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except RuntimeError as error:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})
            return
        self._send_json(HTTPStatus.OK, result)

    def do_PUT(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _events(self, query: str) -> dict[str, object]:
        values = parse_qs(query)
        cursor = values.get("cursor", [""])[0]
        try:
            limit = int(values.get("limit", ["50"])[0])
        except ValueError as error:
            raise ValueError("event limit must be an integer") from error
        runtime = self.server.runtime
        if runtime.container is None:
            return {
                "items": [],
                "cursor": "0",
                "next_cursor": "0",
                "has_more": False,
            }
        return runtime.container.operations.events_page(cursor, limit)

    def _method_not_allowed(self) -> None:
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "console is read-only"})

    def _read_json(self) -> dict[str, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid content length") from error
        if length <= 0 or length > 65_536:
            raise ValueError("JSON request body must be between 1 and 65536 bytes")
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError("request body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise TypeError("request body must be a JSON object")
        return payload

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        self._send(status, _json_bytes(payload), "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)


class ConsoleServer:
    def __init__(self, runtime, host: str = "127.0.0.1", port: int = 0):
        if host not in LOOPBACK_HOSTS:
            raise ValueError("CTXORA Console only supports loopback hosts")
        if not 0 <= int(port) <= 65_535:
            raise ValueError("console port must be between 0 and 65535")
        self.runtime = runtime
        self.host = host
        self.port = int(port)
        self._server: _ConsoleHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._startup_error: Exception | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            raise RuntimeError("console is not running")
        address = self._server.server_address
        return str(address[0]), int(address[1])

    @property
    def url(self) -> str:
        host, port = self.address
        display_host = f"[{host}]" if ":" in host else host
        return f"http://{display_host}:{port}/"

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> dict[str, object]:
        if self._thread is not None:
            raise RuntimeError("console is already running")
        self._thread = threading.Thread(
            target=self._serve,
            name="ctxora-console",
            daemon=True,
        )
        self._thread.start()
        if not self._started.wait(timeout=30):
            raise TimeoutError("console did not start within 30 seconds")
        if self._startup_error is not None:
            raise self._startup_error
        return {
            "status": "running",
            "read_only": False,
            "safe_actions": True,
            "host": self.address[0],
            "port": self.address[1],
            "url": self.url,
        }

    def _serve(self) -> None:
        try:
            if self.runtime.container is None:
                self.runtime.startup()
            server_type = _ConsoleHTTPServerV6 if self.host == "::1" else _ConsoleHTTPServer
            self._server = server_type((self.host, self.port), _ConsoleHandler, self.runtime)
        except Exception as error:  # noqa: BLE001 - propagate worker startup failures.
            self._startup_error = error
            self._started.set()
            return
        self._started.set()
        self._server.serve_forever()

    def wait(self) -> None:
        if self._thread is None:
            raise RuntimeError("console is not running")
        self._thread.join()

    def shutdown(self) -> None:
        server, thread = self._server, self._thread
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._server = None
        self._thread = None


_CONSOLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CTXORA Console</title>
  <style>
    :root{--ink:#191c1b;--paper:#ece9df;--panel:#f7f3e8;--line:#b9b4a7;--green:#1b6b4a;--amber:#c98218;--muted:#676960}
    *{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font-family:Georgia,'Times New Roman',serif}
    body:before{content:'';position:fixed;inset:0;pointer-events:none;opacity:.16;background-image:repeating-linear-gradient(0deg,transparent 0 3px,#777 4px)}
    header{display:flex;justify-content:space-between;gap:2rem;align-items:flex-end;padding:2.2rem 3vw 1.4rem;border-bottom:2px solid var(--ink)}
    h1{font-size:clamp(2.2rem,6vw,5.4rem);line-height:.82;letter-spacing:-.06em;margin:0}header p{max-width:34rem;margin:0;color:var(--muted)}
    main{padding:1.5rem 3vw 4rem}.strip{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);background:var(--panel);margin-bottom:1.4rem}
    .metric{padding:1rem;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric b{display:block;font:700 1.6rem ui-monospace,monospace}.metric span,.label{font:700 .7rem ui-monospace,monospace;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:1rem}.panel{grid-column:span 4;background:var(--panel);border:1px solid var(--line);padding:1.1rem;min-height:12rem;box-shadow:4px 4px 0 #d2cec2}
    .wide{grid-column:span 8}.full{grid-column:1/-1}.panel h2{display:flex;justify-content:space-between;align-items:center;margin:0 0 1rem;font-size:1.05rem;border-bottom:1px solid var(--line);padding-bottom:.65rem}
    .dot{width:.65rem;height:.65rem;border-radius:50%;background:var(--amber);box-shadow:0 0 0 4px #c9821822}.dot.ready{background:var(--green);box-shadow:0 0 0 4px #1b6b4a22}
    dl{display:grid;grid-template-columns:1fr auto;gap:.55rem;margin:0}dt{color:var(--muted)}dd{margin:0;font:700 .8rem ui-monospace,monospace;text-align:right;overflow-wrap:anywhere}
    table{width:100%;border-collapse:collapse;font:.78rem ui-monospace,monospace}th,td{text-align:left;padding:.65rem;border-bottom:1px solid var(--line)}th{color:var(--muted);text-transform:uppercase;font-size:.65rem;letter-spacing:.08em}
    .empty{color:var(--muted);font-style:italic}.badge{padding:.2rem .45rem;border:1px solid currentColor;font:.65rem ui-monospace,monospace}.live{color:var(--green)}#events{max-height:24rem;overflow:auto}
    .hint{margin:.2rem 0 1rem;color:var(--muted);font-size:.82rem}#task-history{max-height:20rem;overflow:auto}
    .action-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:.7rem}.action-grid select,.action-grid input,.action-grid button{min-width:0;padding:.7rem;border:1px solid var(--line);background:#fffdf6;color:var(--ink);font:700 .75rem ui-monospace,monospace}.action-grid button{cursor:pointer;background:var(--ink);color:var(--panel)}.action-grid button:disabled{cursor:not-allowed;opacity:.38}.action-result{margin-top:1rem;padding:.8rem;background:#ebe7dc;white-space:pre-wrap;overflow-wrap:anywhere;font:.72rem ui-monospace,monospace}
    footer{padding:0 3vw 2rem;color:var(--muted);font:.7rem ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em}
    @media(max-width:900px){header{display:block}header p{margin-top:1rem}.strip{grid-template-columns:repeat(2,1fr)}.panel,.wide{grid-column:1/-1}}
  </style>
</head>
<body>
  <header><div><div class="label">Local operator surface</div><h1>CTXORA<br>Console</h1></div><p>Runtime health, context quality, learning, and a narrow set of planned, confirmed workspace actions.</p></header>
  <main>
    <section class="strip" id="overview" aria-label="Overview"><div class="metric"><span>Status</span><b id="status">Connecting</b></div><div class="metric"><span>Files</span><b id="files">—</b></div><div class="metric"><span>Chunks</span><b id="chunks">—</b></div><div class="metric"><span>Tokens</span><b id="tokens">—</b></div></section>
    <div class="grid">
      <section class="panel" id="index-health"><h2>Index Health <i class="dot" id="health-dot"></i></h2><dl id="index"></dl></section>
      <section class="panel" id="retrieval"><h2>Retrieval <span class="badge">local</span></h2><dl id="retrieval-data"></dl></section>
      <section class="panel" id="memory-handoffs"><h2>Memory / Handoffs</h2><dl id="memory-data"></dl></section>
      <section class="panel" id="skills"><h2>Skills</h2><dl id="skills-data"></dl></section>
      <section class="panel wide" id="install-targets"><h2>Install Targets</h2><div id="installs" class="empty">No receipts.</div></section>
      <section class="panel full" id="task-learning"><h2>Task Learning <span class="badge">fingerprint only</span></h2><p class="hint">Completed outcomes update project-scoped reranking. Raw prompts and transcripts are never stored.</p><div id="task-history" class="empty">No routed tasks.</div></section>
      <section class="panel full" id="safe-actions"><h2>Safe Actions <span class="badge">plan + confirm</span></h2><p class="hint">Preview a deterministic plan first. Confirm executes only the stored digest; arbitrary commands and external paths are rejected.</p><div class="action-grid"><select id="action"><option value="refresh">Refresh</option><option value="invalidate">Invalidate</option><option value="purge_expired_handoffs">Purge expired handoffs</option><option value="repair_index">Repair index</option><option value="diagnostics_export">Diagnostics export</option><option value="install_preview">Install preview</option><option value="update_check">Check for update</option><option value="update_plan">Create update plan</option></select><input id="action-target" placeholder="target: all / codex"><input id="action-profile" placeholder="profile: developer"><input id="action-output" placeholder="output / export name"><button id="plan-action" disabled>Preview plan</button><button id="confirm-action" disabled>Confirm</button></div><div class="action-result" id="action-result">Loading action policy…</div></section>
      <section class="panel full" id="events-panel"><h2>Events <span class="badge live" id="event-state">SSE</span></h2><div id="events" class="empty">No events.</div></section>
    </div>
  </main>
  <footer>Loopback only · Allowlisted actions · CSRF protected · No customer content in telemetry</footer>
  <script>
    const text=(id,value)=>document.getElementById(id).textContent=value;
    const pairs=(id,data)=>{const root=document.getElementById(id);root.replaceChildren();Object.entries(data||{}).forEach(([key,value])=>{const dt=document.createElement('dt');const dd=document.createElement('dd');dt.textContent=key.replaceAll('_',' ');dd.textContent=typeof value==='object'?JSON.stringify(value):String(value);root.append(dt,dd)})};
    const renderEvents=page=>{const root=document.getElementById('events');const items=page?.items||[];root.replaceChildren();if(!items.length){root.className='empty';root.textContent='No events.';return}root.className='';const table=document.createElement('table');table.innerHTML='<thead><tr><th>Time</th><th>Event</th><th>Method / Action</th><th>Outcome</th><th>Duration</th></tr></thead>';const body=document.createElement('tbody');items.slice().reverse().forEach(item=>{const row=document.createElement('tr');[item.timestamp,item.event,item.method??item.action??'—',item.outcome??item.status??'—',item.duration_ms??'—'].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;row.append(cell)});body.append(row)});table.append(body);root.append(table)};
    const renderTasks=skills=>{const root=document.getElementById('task-history');const recent=(skills?.recent_tasks||[]).map(item=>({...item,state:item.outcome,skills:item.used_skills?.length?item.used_skills:item.affected_skills,time:item.completed_at}));const pending=(skills?.pending_tasks||[]).map(item=>({...item,state:'pending',skills:item.recommended_skills,time:item.created_at}));const tasks=[...recent,...pending];root.replaceChildren();if(!tasks.length){root.className='empty';root.textContent='No routed tasks.';return}root.className='';const table=document.createElement('table');table.innerHTML='<thead><tr><th>Task fingerprint</th><th>State</th><th>Skills</th><th>Time</th></tr></thead>';const body=document.createElement('tbody');tasks.forEach(item=>{const row=document.createElement('tr');[item.task_fingerprint,item.state,(item.skills||[]).join(', ')||'—',item.time?new Date(item.time*1000).toLocaleString():'—'].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;row.append(cell)});body.append(row)});table.append(body);root.append(table)};
    const render=s=>{text('status',s.status||'unknown');text('files',s.index?.files??0);text('chunks',s.index?.chunks??0);text('tokens',(s.index?.tokens??0).toLocaleString());document.getElementById('health-dot').classList.toggle('ready',Boolean(s.ready));pairs('index',{snapshot:s.snapshot?.snapshot_id?.slice(0,12)||'none',version:s.snapshot?.snapshot_version??0,current:s.index?.current??false,edges:s.index?.graph_edges??0,bundles:s.index?.bundles??0});pairs('retrieval-data',{latency_ms:s.retrieval?.last_retrieval_ms??0,coverage:s.retrieval?.last_coverage??'unknown',ecc:s.retrieval?.adapters?.ecc?.enabled??false});pairs('memory-data',{memories:s.memory?.total??0,handoffs:s.handoffs?.count??0});pairs('skills-data',{learned:s.skills?.learned_skills?.length??0,completed_tasks:s.skills?.completed_tasks??0,pending_routes:s.skills?.pending_routes??0,boosted_skills:s.skills?.reranking?.boosted_skills??0,penalized_skills:s.skills?.reranking?.penalized_skills??0});const receipts=s.installer?.receipts||[];const installs=document.getElementById('installs');installs.textContent=receipts.length?receipts.map(r=>`${r.target||'unknown'} · ${r.profile||'default'} · ${r.verified?'verified':'unverified'}`).join(' | '):'No receipts.';renderTasks(s.skills);renderEvents(s.events)};
    fetch('/api/snapshot').then(r=>r.json()).then(render).catch(()=>text('status','offline'));
    let csrf='';let plannedDigest='';const result=document.getElementById('action-result');const confirm=document.getElementById('confirm-action');const planButton=document.getElementById('plan-action');
    fetch('/api/actions').then(r=>r.json()).then(data=>{csrf=data.csrf_token;planButton.disabled=false;result.textContent='No action planned.'}).catch(()=>{result.textContent='Action policy unavailable.'});
    const actionParameters=()=>{const action=document.getElementById('action').value;const target=document.getElementById('action-target').value.trim();const profile=document.getElementById('action-profile').value.trim();const output=document.getElementById('action-output').value.trim();if(action==='invalidate')return {target:target||'all'};if(action==='diagnostics_export')return {name:output||'ctxora-diagnostics.json'};if(action==='install_preview'){const value={target:target||'codex',profile:profile||'developer'};if(value.target==='custom')value.output=output;return value}return {}};
    const postAction=(path,payload)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CTXORA-CSRF':csrf},body:JSON.stringify(payload)}).then(async response=>{const data=await response.json();if(!response.ok)throw new Error(data.error||'Action failed');return data});
    const clearPlan=()=>{plannedDigest='';confirm.disabled=true;result.textContent='Inputs changed. Preview a new plan.'};['action','action-target','action-profile','action-output'].forEach(id=>document.getElementById(id).addEventListener('change',clearPlan));
    planButton.onclick=()=>{planButton.disabled=true;confirm.disabled=true;plannedDigest='';result.textContent='Planning…';postAction('/api/actions/plan',{action:document.getElementById('action').value,parameters:actionParameters()}).then(plan=>{plannedDigest=plan.digest;confirm.disabled=false;result.textContent=JSON.stringify(plan,null,2)}).catch(error=>{result.textContent=error.message}).finally(()=>{planButton.disabled=false})};
    confirm.onclick=()=>{confirm.disabled=true;result.textContent='Executing confirmed plan…';postAction('/api/actions/execute',{plan_digest:plannedDigest,confirm:true}).then(receipt=>{plannedDigest='';result.textContent=JSON.stringify(receipt,null,2);return fetch('/api/snapshot')}).then(response=>response?.json()).then(snapshot=>{if(snapshot)render(snapshot)}).catch(error=>{result.textContent=error.message})};
    const stream=new EventSource('/events?limit=20');stream.addEventListener('events',event=>renderEvents(JSON.parse(event.data)));stream.onerror=()=>text('event-state','SSE pulse');stream.onopen=()=>text('event-state','SSE live');
  </script>
</body>
</html>
"""
