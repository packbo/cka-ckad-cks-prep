"""Web exam server with a REAL web terminal (xterm.js + PTY over WebSocket).

Layout: questions/buttons on the LEFT, a full bash terminal on the RIGHT
(split draggable) — like Killercoda. The terminal is a true PTY: bash
completion, vim, top, Ctrl+C … all work.

Extra: "AI assisted Learning" tab — exercises generated live by an AI agent
(opencode) are dropped in scenarios/ai/<id>/scenario.yaml and hot-loaded by
/api/ai/* without restarting the server or breaking the exam UI.

Run in-cluster (deployed by ./run.sh web) or locally (existing cluster):
    http://localhost:8080
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import pty
import shlex
import signal
import struct
import subprocess
import termios
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from cka_sim import paths
from cka_sim.cluster import run_shell
from cka_sim.engine import load_assertions, load_scenarios
from cka_sim.hints import PENALTY
from cka_sim.paths import CHEATSHEET_PATH, EXAMS_ROOT

_CERT = os.environ.get("CKA_SIM_CERT", "cka")
EXAM_FILE = os.environ.get("CKA_SIM_EXAM", f"{_CERT}/web-exam.yaml")
PORT = int(os.environ.get("CKA_SIM_WEB_PORT", "8080"))

AI_CERT = "ai"
AI_EXAM = "assisted"


def available_exams() -> list:
    """List all exam yaml files across all certs."""
    import glob
    exams = []
    for f in sorted(glob.glob(os.path.join(EXAMS_ROOT, "*", "*.yaml"))):
        rel = os.path.relpath(f, EXAMS_ROOT)
        cert = rel.split(os.sep)[0] if os.sep in rel else "?"
        name = os.path.basename(f).replace(".yaml", "")
        exams.append({"cert": cert, "name": name, "path": rel})
    return exams


# ---------------------------------------------------------------- state ----
class ExamState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.started_at = None
        self.questions = []      # dicts: scenario + status/score/hints
        self.minutes = 0
        self.threshold = 66
        self.advisory = ""
        self.env = {"nodes": 0, "workers": 0}
        self.cert = _CERT
        self.exam_name = "web-exam.yaml"

    def load(self, cert=None, exam_name=None) -> None:
        global EXAM_FILE
        if cert:
            paths.set_cert(cert)
            self.cert = cert
        if exam_name:
            self.exam_name = exam_name
        EXAM_FILE = f"{self.cert}/{self.exam_name}"
        exam_path = os.path.join(EXAMS_ROOT, EXAM_FILE)
        with open(exam_path) as fh:
            exam = yaml.safe_load(fh)
        self.minutes = int(exam.get("minutes", 120))
        self.threshold = int(exam.get("threshold", 66))
        by_id = {s.id: s for s in load_scenarios()}
        from cka_sim import env as _env
        e = _env.detect()
        self.advisory = _env.advisory(e)
        self.env = {"nodes": e["nodes"], "workers": len(e["workers"])}
        self.questions = []

        # restore saved state from SQLite
        from cka_sim import db
        saved = db.load_questions(self.cert, self.exam_name)
        sess = db.load_session()
        if sess.get("elapsed") and not self.started_at:
            self.started_at = time.time() - int(sess["elapsed"])
        if sess.get("started_at") and not self.started_at:
            self.started_at = sess["started_at"]

        for sid in exam.get("scenarios", []):
            s = by_id.get(sid)
            if s is None:
                continue
            if _env.unmet_requires(s.requires, e):
                continue
            # restore per-question state (legacy 'solved' -> 'done')
            prev = saved.get(sid, {})
            status = prev.get("status", "pending")
            if status == "solved":
                status = "done"
            # SALVAGE: score > 0 can only have been earned by a passed check
            # (old code sometimes saved 'active' with the score already set)
            if float(prev.get("score", 0.0)) > 0 and status != "done":
                status = "done"
            self.questions.append({
                "scenario": s,
                "status": status,
                "score": prev.get("score", 0.0),
                "hints_used": prev.get("hints_used", 0),
            })

        # persist session metadata
        db.save_session(
            cert=self.cert,
            exam=self.exam_name,
            elapsed=self.elapsed(),
            started_at=self.started_at,
        )

    def elapsed(self) -> int:
        return int(time.time() - self.started_at) if self.started_at else 0

    def persist(self):
        """Save all question states + session metadata to SQLite."""
        from cka_sim import db
        for q in self.questions:
            db.save_question(
                self.cert, self.exam_name,
                q["scenario"].id, q["status"], q["score"], q["hints_used"],
            )
        db.save_session(
            cert=self.cert, exam=self.exam_name,
            elapsed=self.elapsed(), started_at=self.started_at,
        )

    def public(self) -> dict:
        with self.lock:
            return {
                "minutes": self.minutes,
                "threshold": self.threshold,
                "elapsed": self.elapsed(),
                "advisory": self.advisory,
                "env": self.env,
                "cert": self.cert,
                "examName": self.exam_name,
                "questions": [
                    {
                        "index": i,
                        "id": q["scenario"].id,
                        "title": q["scenario"].title,
                        "domain": q["scenario"].domain,
                        "weight": q["scenario"].weight,
                        "difficulty": q["scenario"].difficulty,
                        "status": q["status"],
                        "score": q["score"],
                        "hints_used": q["hints_used"],
                    }
                    for i, q in enumerate(self.questions)
                ],
            }

    def report(self) -> dict:
        with self.lock:
            total = sum(q["scenario"].weight for q in self.questions)
            earned = sum(q["score"] for q in self.questions)
            dom = defaultdict(lambda: [0.0, 0.0])
            for q in self.questions:
                dom[q["scenario"].domain][0] += q["score"]
                dom[q["scenario"].domain][1] += q["scenario"].weight
            pct = round(earned / total * 100, 1) if total else 0.0
            return {
                "earned": round(earned, 2),
                "total": total,
                "percent": pct,
                "passed": pct >= self.threshold,
                "threshold": self.threshold,
                "elapsed": self.elapsed(),
                "domains": [
                    {"domain": d, "score": v[0], "max": v[1]}
                    for d, v in sorted(dom.items())
                ],
                "questions": [
                    {"id": q["scenario"].id, "status": q["status"],
                     "score": q["score"], "weight": q["scenario"].weight,
                     "hints": q["hints_used"]}
                    for q in self.questions
                ],
            }


STATE = ExamState()


# ------------------------------------------------- AI-assisted Learning ----
def _load_ai_bank() -> "list":
    """Hot-load scenarios/ai/*/scenario.yaml — safe to call on every request.

    The AI agent (opencode) drops new exercise folders there at runtime;
    they appear in the web UI on the next list/refresh, without restart.
    """
    from cka_sim.engine import _load as _load_scenario
    root = os.path.join(paths.SCENARIOS_ROOT, AI_CERT)
    out = []
    if not os.path.isdir(root):
        return out
    for dirpath, _, files in os.walk(root):
        if "scenario.yaml" not in files:
            continue
        try:
            out.append(_load_scenario(os.path.join(dirpath, "scenario.yaml")))
        except Exception as e:
            out.append(None)
    scenarios = sorted((s for s in out if s), key=lambda s: s.id)
    # merge persisted progress (cert='ai', exam='assisted')
    from cka_sim import db
    saved = db.load_questions(AI_CERT, AI_EXAM)
    result = []
    for s in scenarios:
        prev = saved.get(s.id, {})
        status = prev.get("status", "pending")
        if status == "solved":  # legacy value -> 'done'
            status = "done"
        result.append({
            "id": s.id,
            "title": s.title,
            "domain": s.domain,
            "weight": s.weight,
            "difficulty": s.difficulty,
            "status": status,
            "score": prev.get("score", 0.0),
            "hints_used": prev.get("hints_used", 0),
            "mtime": int(os.path.getmtime(s.path)),
        })
    return result


def _ai_scenario(scenario_id: str):
    for item in _load_ai_bank():
        if item["id"] == scenario_id:
            return item
    return None


def _ai_apply_setup(scenario_id: str, delete_first: bool = True):
    """Apply (or reset) the setup manifest of an AI exercise."""
    from cka_sim.engine import _load as _load_scenario
    sp = os.path.join(paths.SCENARIOS_ROOT, AI_CERT, scenario_id, "setup.yaml")
    if not os.path.exists(sp):
        return False
    if delete_first:
        run_shell(
            f"kubectl delete -f {sp} --ignore-not-found --wait=true --timeout=30s",
            timeout=60,
        )
    run_shell(f"kubectl apply -f {sp}")
    return True


def _ai_persist(scenario_id: str, status: str, score: float, hints_used: int):
    from cka_sim import db
    db.save_question(AI_CERT, AI_EXAM, scenario_id, status, score, hints_used)


def _ai_report() -> dict:
    items = _load_ai_bank()
    total = sum(i["weight"] for i in items)
    earned = sum(i["score"] for i in items)
    done_count = sum(1 for i in items if i["status"] == "done")
    return {
        "count": len(items),
        "solved": done_count,
        "earned": round(earned, 2),
        "total": total,
        "percent": round(earned / total * 100, 1) if total else 0.0,
    }


def load_cheatsheet() -> dict:
    try:
        with open(CHEATSHEET_PATH) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {"research_methods": []}


def _run_setup_scripts(scenario) -> str:
    """Run break/fix setup scripts (setup.script:) with %PLACEHOLDER%
    substitution. Returns error text ('' = ok)."""
    from cka_sim import env as _env
    if not scenario.setup_script:
        return ""
    for n, cmd in enumerate(scenario.setup_script, 1):
        cp = run_shell(_env.substitute(cmd), timeout=180)
        if cp.returncode != 0:
            return (f"setup script step {n}/{len(scenario.setup_script)} failed: "
                    + ((cp.stderr or "") + (cp.stdout or "")).strip()[-400:])
    return ""


def _apply_setup_manifest(path: str):
    """kubectl apply a setup manifest with one retry (transient API errors at
    cluster cold-start). Comment-only / empty manifests are a no-op SUCCESS
    (some scenarios have no cluster resources). Returns (ok, error_text)."""
    try:
        docs = [d for d in yaml.safe_load_all(open(path)) if d]
    except FileNotFoundError:
        return True, ""  # nothing to apply
    if not docs:
        return True, ""  # comments only — nothing to create
    cp = None
    for attempt in (1, 2):
        cp = run_shell(f"kubectl apply -f {path}", timeout=60)
        if cp.returncode == 0:
            return True, ""
        if "no objects passed to apply" in (cp.stderr or "") + (cp.stdout or ""):
            return True, ""  # defensive: manifest parsed empty by kubectl
        if attempt == 1:
            time.sleep(2)
    return False, ((cp.stderr or "") + (cp.stdout or "")).strip()[-500:] \
        or "kubectl apply failed"


def _tag_or_untag(scenario_id: str, tag: bool, note=None):
    from cka_sim import review as _review
    if tag:
        _review.tag(scenario_id, note)
    else:
        _review.untag(scenario_id)


def access_info() -> dict:
    """NodePort + node IPs of the current cluster (for the Access tab)."""
    port = run_shell(
        "kubectl get svc cka-exam -o jsonpath='{.spec.ports[0].nodePort}'"
    ).stdout.strip()
    ips = [
        line
        for line in run_shell(
            "kubectl get nodes -o jsonpath="
            "'{range .items[*]}{.status.addresses[?(@.type==\"InternalIP\")].address}{\"\\n\"}{end}'"
        ).stdout.split()
        if line
    ]
    return {"nodePort": port, "nodeIPs": ips}


TOOL_MAP = {"k": "kubectl", "kubectl": "kubectl"}
NO_SANDBOX = {"helm", "kubeadm", "k9s", "istioctl", "kubectl-krew"}


def complete_command(text: str) -> dict:
    """Shell completion for the legacy one-shot /api/cmd endpoint."""
    text = (text or "").lstrip()
    if not text:
        return {"suggestions": ["kubectl ", "k "], "note": "start with kubectl…"}
    try:
        words = shlex.split(text)
    except ValueError:
        words = text.split()
    if text.endswith(" ") or not words:
        words = words + [""]
    first = words[0]
    if first in NO_SANDBOX:
        return {
            "suggestions": [],
            "note": f"'{first}' is not available in this sandbox.",
        }
    tool = TOOL_MAP.get(first)
    if tool is None:
        return {"suggestions": [], "note": "completion covers kubectl / k."}
    try:
        cp = subprocess.run([tool, "__complete"] + words[1:],
                            capture_output=True, text=True, timeout=10)
    except Exception:
        return {"suggestions": [], "note": "completion unavailable"}
    suggestions = []
    for line in (cp.stdout or "").splitlines():
        if line.startswith(":"):
            break
        if line.strip():
            suggestions.append(line.strip())
    return {"suggestions": suggestions[:40]}


# ------------------------------------------------------------- kubeconfig --
def ensure_kubeconfig() -> None:
    """When running in-cluster, build a kubeconfig from the ServiceAccount."""
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    if not host:
        return
    port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS",
                          os.environ.get("KUBERNETES_SERVICE_PORT", "443"))
    sa = "/var/run/secrets/kubernetes.io/serviceaccount"
    token = open(os.path.join(sa, "token")).read().strip()
    home = os.path.expanduser("~")
    os.makedirs(os.path.join(home, ".kube"), exist_ok=True)
    cfg = (
        "apiVersion: v1\nkind: Config\n"
        f"clusters:\n- cluster:\n    server: https://{host}:{port}\n"
        f"    certificate-authority: {sa}/ca.crt\n  name: cka\n"
        "contexts:\n- context:\n    cluster: cka\n    user: sa\n"
        "    namespace: default\n  name: cka\ncurrent-context: cka\n"
        "users:\n- name: sa\n  user:\n    token: " + token + "\n"
    )
    with open(os.path.join(home, ".kube", "config"), "w") as fh:
        fh.write(cfg)


# ======================================================== WEB TERMINAL ====
# Real bash in a PTY, served over WebSocket (RFC 6455) — same approach as
# ttyd / Killercoda: xterm.js in the browser <-> PTY on the server.
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _ws_accept_key(key: str) -> str:
    digest = hashlib.sha1((key + WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def _ws_encode(opcode: int, payload: bytes) -> bytes:
    """Encode one server->client frame (unmasked, as required)."""
    header = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header += bytes([n])
    elif n < 65536:
        header += bytes([126]) + struct.pack(">H", n)
    else:
        header += bytes([127]) + struct.pack(">Q", n)
    return header + payload


def _ws_read_exact(rfile, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = rfile.read(n - len(buf))
        if not chunk:
            raise ConnectionError("client closed mid-frame")
        buf += chunk
    return buf


def _ws_decode_frame(rfile):
    """Read + unmask one client->server frame. Returns (opcode, payload)."""
    b1, b2 = _ws_read_exact(rfile, 2)
    fin_op = b1 & 0x0F
    masked = b2 & 0x80
    length = b2 & 0x7F
    if length == 126:
        (length,) = struct.unpack(">H", _ws_read_exact(rfile, 2))
    elif length == 127:
        (length,) = struct.unpack(">Q", _ws_read_exact(rfile, 8))
    mask = _ws_read_exact(rfile, 4) if masked else b"\x00\x00\x00\x00"
    payload = bytearray(_ws_read_exact(rfile, length))
    if masked:
        for i in range(length):
            payload[i] ^= mask[i % 4]
    return fin_op, bytes(payload)


def _pty_resize(fd: int, cols: int, rows: int) -> None:
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass


class TerminalSession:
    """One shared bash PTY (like Killercoda: survives page reloads).

    - started lazily on first terminal connection
    - exactly one browser client attached at a time (new one wins)
    - reader thread streams PTY output to the attached client as binary WS
      frames; browser keystrokes arrive as JSON text frames
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.send_lock = threading.Lock()
        self.pid: int | None = None
        self.master: int | None = None
        self.client_sock = None          # raw socket of the attached browser
        self.client_rfile = None
        self.alive = False
        self.started_at = 0.0

    # ── lifecycle ────────────────────────────────────────────────────────
    def start(self) -> None:
        self.stop()
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["PS1"] = r"\[\e]0;\u@\h:\w\a\]\[\e[1;32m\]\u@cka-sim\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\$ "
        env.setdefault("HOME", "/root" if os.geteuid() == 0 else "/home/user")
        env.setdefault("KUBECONFIG", os.path.join(env["HOME"], ".kube", "config"))
        cwd = env["HOME"] if os.path.isdir(env["HOME"]) else "/"

        pid, master = pty.fork()
        if pid == 0:  # child — becomes session leader with the pty as tty
            try:
                os.chdir(cwd)
                os.execvpe("bash", ["bash", "-i"], env)
            except Exception:
                os._exit(127)

        self.pid = pid
        self.master = master
        self.alive = True
        self.started_at = time.time()
        _pty_resize(master, 80, 24)
        threading.Thread(target=self._reader, daemon=True).start()

    def stop(self) -> None:
        self.alive = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
        self.pid, self.master = None, None

    def is_alive(self) -> bool:
        if not self.alive or self.pid is None:
            return False
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            self.alive = False
            return False
        if pid == self.pid:  # exited
            self.alive = False
            return False
        return True

    # ── IO ───────────────────────────────────────────────────────────────
    def _reader(self) -> None:
        """PTY output -> attached client (binary WS frames)."""
        import select
        while self.alive:
            try:
                r, _, _ = select.select([self.master], [], [], 0.2)
                if not r:
                    continue
                data = os.read(self.master, 65536)
            except OSError:
                break
            if not data:
                break
            self.broadcast(data)
        self.alive = False
        # let the browser know the shell died; it will offer a restart
        try:
            self.broadcast("[session ended - press Reconnect to start a new shell]\r\n".encode())
        except Exception:
            pass

    def broadcast(self, data: bytes) -> None:
        sock = self.client_sock
        if sock is None:
            return
        frame = _ws_encode(0x2, data)  # binary frame
        with self.send_lock:
            try:
                sock.sendall(frame)
            except OSError:
                self.client_sock = None

    def write(self, data: bytes) -> None:
        if self.master is None:
            return
        try:
            os.write(self.master, data)
        except OSError:
            pass

    def resize(self, cols: int, rows: int) -> None:
        if self.master is None or self.pid is None:
            return
        _pty_resize(self.master, cols, rows)
        try:
            os.kill(self.pid, signal.SIGWINCH)
        except ProcessLookupError:
            pass


TERM = TerminalSession()


def _handle_ws_terminal(handler: "Handler") -> None:
    """Upgrade an HTTP request to a WebSocket and bridge it to the PTY."""
    key = handler.headers.get("Sec-WebSocket-Key")
    if not key:
        handler._json({"error": "missing Sec-WebSocket-Key"}, 400)
        return

    # --- handshake ---
    handler.send_response(101, "Switching Protocols")
    handler.send_header("Upgrade", "websocket")
    handler.send_header("Connection", "Upgrade")
    handler.send_header("Sec-WebSocket-Accept", _ws_accept_key(key))
    handler.end_headers()
    handler.close_connection = True

    sock = handler.connection
    rfile = handler.rfile

    # single client wins: detach any previous one
    with TERM.lock:
        TERM.client_sock = sock
    if not TERM.is_alive():
        TERM.start()

    # tell the browser the session is live (text frame, JSON)
    try:
        with TERM.send_lock:
            sock.sendall(_ws_encode(0x1, json.dumps(
                {"status": "attached", "restart": int(time.time() - TERM.started_at) > 0}
            ).encode()))
    except OSError:
        return

    try:
        while True:
            opcode, payload = _ws_decode_frame(rfile)
            if opcode == 0x8:  # close
                with TERM.send_lock:
                    try:
                        sock.sendall(_ws_encode(0x8, payload[:0] + b"\x03\xe8"))
                    except OSError:
                        pass
                break
            if opcode == 0x9:  # ping -> pong
                with TERM.send_lock:
                    sock.sendall(_ws_encode(0xA, payload))
                continue
            if opcode == 0xA:  # pong
                continue
            if opcode in (0x1, 0x2, 0x0):  # text / binary / continuation
                try:
                    msg = json.loads(payload.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if "input" in msg:
                    TERM.write(str(msg["input"]).encode())
                if "resize" in msg:
                    cols, rows = msg["resize"][:2]
                    TERM.resize(int(cols), int(rows))
    except (ConnectionError, OSError):
        pass
    finally:
        with TERM.lock:
            if TERM.client_sock is sock:
                TERM.client_sock = None


# --------------------------------------------------------------- handler --
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    _MIME = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
    }

    def _serve_static(self):
        """Serve static files from cka_sim/static/ (incl. vendored xterm)."""
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "static"
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            rel = pathlib.Path("index.html")
        else:
            rel = pathlib.Path(path.lstrip("/"))
        # prevent path traversal
        if ".." in rel.parts:
            return self._json({"error": "bad path"}, 400)
        f = static_dir / rel
        if not f.is_file():
            return self._json({"error": "not found", "path": path}, 404)
        body = f.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", self._MIME.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/ws"):
            return _handle_ws_terminal(self)
        if self.path.split("?", 1)[0] in ("/", "/index.html") \
                or self.path.startswith("/vendor/"):
            return self._serve_static()
        if self.path == "/api/state":
            self._json(STATE.public())
        elif self.path == "/api/report":
            self._json(STATE.report())
        elif self.path == "/api/cheatsheet":
            self._json(load_cheatsheet())
        elif self.path == "/api/access":
            self._json(access_info())
        elif self.path == "/api/exams":
            self._json({"exams": available_exams()})
        elif self.path.startswith("/api/ai/chat"):
            return self._ai_chat_get()
        elif self.path == "/api/ai/list":
            self._json({"exercises": _load_ai_bank()})
        elif self.path == "/api/ai/report":
            self._json(_ai_report())
        elif self.path == "/api/db/download":
            self._db_download()
        elif self.path == "/api/db/info":
            self._db_info()
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        # raw binary DB upload (no base64/json): body IS the sqlite file
        if self.path == "/api/db/upload-raw":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            return self._import_db_bytes(raw)

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)

        p = self.path.replace("/api/", "")
        p = self.path.replace("/api/", "")
        if p.startswith("ai/chat"):
            return self._ai_chat_post(p, data)
        if p.startswith("ai/"):
            return self._dispatch_ai(p, data)
        with STATE.lock:
            if p == "start":
                return self._api_start(data)
            if p == "question":
                return self._api_question(data)
            if p == "cmd":
                return self._api_cmd(data)
            if p == "hint":
                return self._api_hint(data)
            if p == "check":
                return self._api_check(data)
            if p == "skip":
                return self._api_skip(data)
            if p == "tag":
                return self._api_tag(data)
            if p == "reset":
                return self._api_reset(data)
            if p == "cert":
                return self._api_cert(data)
            if p == "db/reset":
                return self._api_db_reset(data)
            if p == "db/upload":
                return self._api_db_upload(data)
            if p == "complete":
                return self._json(complete_command(str(data.get("input", ""))))
        self._json({"error": "unknown endpoint"}, 404)

    # --- AI teacher chat ---------------------------------------------------
    def _ai_chat_get(self):
        """GET /api/ai/chat[?since=<id>] — messages + pending count.

        The AI agent (opencode) polls this; the browser renders the thread.
        """
        from cka_sim import db
        qs = self.path.split("?", 1)
        since = 0
        if len(qs) > 1:
            for kv in qs[1].split("&"):
                if kv.startswith("since="):
                    try:
                        since = int(kv[6:])
                    except ValueError:
                        since = 0
        msgs = db.chat_list(since)
        pending = db.chat_pending()
        return self._json({"messages": msgs, "pending": pending})

    def _ai_chat_post(self, p, data):
        """POST /api/ai/chat           {message}  — from the browser chat box
        POST /api/ai/chat/reply       {text}     — from the AI agent
        """
        from cka_sim import db
        if p == "ai/chat/reply":
            text = str(data.get("text", "")).strip()
            if not text:
                return self._json({"error": "empty reply"}, 400)
            handled = db.chat_mark_all_handled()
            rid = db.chat_add("assistant", text, handled=1)
            return self._json({"ok": True, "id": rid, "marked_handled": handled})
        if p == "ai/chat":
            text = str(data.get("message", "")).strip()
            if not text:
                return self._json({"error": "empty message"}, 400)
            rid = db.chat_add("user", text)
            return self._json({"ok": True, "id": rid})
        return self._json({"error": "unknown chat endpoint"}, 404)

    # --- AI-assisted Learning endpoints -----------------------------------
    def _dispatch_ai(self, p: str, data: dict):
        from cka_sim import env as _env
        from cka_sim.engine import _load as _load_scenario

        sid = str(data.get("id", ""))
        if p == "ai/start":
            scen = None
            for item in _load_ai_bank():
                if item["id"] == sid:
                    scen = _load_scenario(
                        os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "scenario.yaml"))
                    break
            if scen is None:
                return self._json({"error": "unknown exercise"}, 404)
            current = _ai_scenario(sid) or {"status": "pending"}
            # never downgrade a finished exercise: keep 'done' (and its cluster
            # state) — re-applying setup would DELETE the solved resources.
            if current.get("status") not in ("done", "skipped"):
                if os.path.exists(os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "setup.yaml")):
                    ok, err = _apply_setup_manifest(
                        os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "setup.yaml"))
                    if not ok:
                        return self._json({"error": "setup failed", "detail": err}, 503)
                _ai_persist(sid, "active", 0.0, 0)
            return self._json({"ok": True,
                               "question": _env.substitute(scen.question),
                               "title": scen.title,
                               "status": current.get("status", "active")})

        if p == "ai/hint":
            level = int(data.get("level", 1))
            spath = os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "scenario.yaml")
            if not os.path.exists(spath):
                return self._json({"error": "unknown exercise"}, 404)
            scen = _load_scenario(spath)
            for h in scen.hints:
                lvl = h.get("level")
                lvl_n = 4 if isinstance(lvl, str) else int(lvl)
                if lvl_n == level:
                    item = _ai_scenario(sid) or {}
                    hints_used = max(int(item.get("hints_used", 0)), level)
                    _ai_persist(sid, item.get("status", "active"),
                                float(item.get("score", 0.0)), hints_used)
                    return self._json({"text": _env.substitute(h.get("text", "")),
                                       "penalty": PENALTY.get(level, 0)})
            return self._json({"text": "no hint at this level", "penalty": 0})

        if p == "ai/check":
            spath = os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "scenario.yaml")
            if not os.path.exists(spath):
                return self._json({"error": "unknown exercise"}, 404)
            scen = _load_scenario(spath)
            from cka_sim.validator import _evaluate_once
            results = []
            for a in load_assertions(scen):
                r = _evaluate_once(a)
                results.append({"passed": r.passed, "detail": r.detail})
            passed = bool(results) and all(r["passed"] for r in results)
            item = _ai_scenario(sid) or {}
            status, score = item.get("status", "pending"), float(item.get("score", 0.0))
            if passed and status != "done":
                hints_used = int(item.get("hints_used", 0))
                pen = PENALTY.get(hints_used, 0.0) if hints_used < 4 else 1.0
                score = round(max(0.0, scen.weight * (1.0 - pen)), 2)
                status = "done"
                _ai_persist(sid, status, score, hints_used)
            return self._json({"results": results, "passed": passed,
                               "score": score if passed else 0.0,
                               "weight": scen.weight})

        if p == "ai/reset":
            _ai_apply_setup(sid, delete_first=True)
            _ai_persist(sid, "pending", 0.0, 0)
            spath = os.path.join(paths.SCENARIOS_ROOT, AI_CERT, sid, "scenario.yaml")
            if os.path.exists(spath):
                scen = _load_scenario(spath)
                return self._json({"ok": True,
                                   "question": _env.substitute(scen.question)})
            return self._json({"ok": True})

        if p == "ai/skip":
            item = _ai_scenario(sid) or {}
            if item.get("status") not in ("done",):
                _ai_persist(sid, "skipped", float(item.get("score", 0.0)),
                            int(item.get("hints_used", 0)))
            return self._json({"ok": True})

        return self._json({"error": "unknown ai endpoint"}, 404)

    # --- endpoint impls (called under lock) ---
    def _q(self, data):
        i = int(data.get("index", -1))
        if i < 0 or i >= len(STATE.questions):
            return None, None
        return i, STATE.questions[i]

    def _api_start(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        if STATE.started_at is None:
            STATE.started_at = time.time()
        s = q["scenario"]
        # never downgrade a finished/skipped question back to 'active'
        if q["status"] in ("pending", "active"):
            if s.setup_fullpath and os.path.exists(s.setup_fullpath):
                ok, err = _apply_setup_manifest(s.setup_fullpath)
                if not ok:
                    # premise of the question is broken without its setup
                    return self._json({
                        "error": "setup failed",
                        "detail": err,
                        "hint": "check the cluster (kubectl get nodes) then click the question again",
                    }, 503)
            err = _run_setup_scripts(s)
            if err:
                return self._json({"error": "setup failed", "detail": err}, 503)
            q["status"] = "active"
            STATE.persist()  # insurance: 'active' state survives restarts
        from cka_sim import env as _env
        return self._json({"ok": True, "question": _env.substitute(s.question),
                           "status": q["status"]})

    def _api_question(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        from cka_sim import env as _env
        s = q["scenario"]
        shown = []
        for h in s.hints:
            lvl = h.get("level")
            lvl_n = 4 if isinstance(lvl, str) else int(lvl)
            if lvl_n <= q["hints_used"]:
                shown.append(_env.substitute(h.get("text", "")))
        return self._json({"question": _env.substitute(s.question), "hint_logs": shown})

    def _api_cmd(self, data):
        cmd = str(data.get("command", ""))
        if not cmd.strip():
            return self._json({"stdout": "", "stderr": "", "rc": 0})
        cp = run_shell(cmd, timeout=90)
        return self._json({"stdout": cp.stdout or "", "stderr": cp.stderr or "", "rc": cp.returncode})

    def _api_hint(self, data):
        i, q = self._q(data)
        level = int(data.get("level", 1))
        if q is None:
            return self._json({"error": "bad index"}, 400)
        s = q["scenario"]
        for h in s.hints:
            lvl = h.get("level")
            lvl_n = 4 if isinstance(lvl, str) else int(lvl)
            if lvl_n == level:
                q["hints_used"] = max(q["hints_used"], level)
                STATE.persist()
                from cka_sim import env as _env
                return self._json({"text": _env.substitute(h.get("text", "")), "penalty": PENALTY.get(level, 0)})
        return self._json({"text": "no hint at this level", "penalty": 0})

    def _api_check(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        s = q["scenario"]
        from cka_sim import env as _env
        from cka_sim.validator import _evaluate_once
        results = []
        for a in load_assertions(s):
            r = _evaluate_once(a)  # single-pass: no settle-retry for web
            results.append({"passed": r.passed, "detail": r.detail})
        passed = bool(results) and all(r["passed"] for r in results)
        if passed:
            if q["status"] != "done":
                pen = PENALTY.get(q["hints_used"], 0.0) if q["hints_used"] < 4 else 1.0
                q["score"] = round(max(0.0, s.weight * (1.0 - pen)), 2)
                q["status"] = "done"
            # persist on EVERY pass (after score/status are set — the old
            # code persisted before updating, so solved questions were saved
            # as active/0 and results looked lost after import/restart);
            # re-persisting on an already-done question also heals stale rows
            STATE.persist()
        return self._json({
            "results": results,
            "passed": passed,
            "score": q["score"] if passed else 0.0,
            "weight": s.weight,
        })

    def _api_skip(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        if q["status"] != "done":
            q["status"] = "skipped"
        STATE.persist()
        return self._json({"ok": True})

    def _api_tag(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        from cka_sim import review as _review
        sid = q["scenario"].id
        currently = _review.is_tagged(sid)
        _tag_or_untag(sid, not currently, data.get("note"))
        return self._json({"ok": True, "tagged": not currently})

    def _api_reset(self, data):
        i, q = self._q(data)
        if q is None:
            return self._json({"error": "bad index"}, 400)
        s = q["scenario"]
        sp = s.setup_fullpath
        warning = ""
        if sp and os.path.exists(sp):
            run_shell(f"kubectl delete -f {sp} --ignore-not-found --wait=true --timeout=30s", timeout=60)
            ok, warning = _apply_setup_manifest(sp)
            if ok:
                warning = ""
        q["status"] = "pending"
        q["hints_used"] = 0
        from cka_sim import env as _env
        return self._json({"ok": True, "question": _env.substitute(s.question),
                           "warning": warning})

    def _api_cert(self, data):
        cert = str(data.get("cert", "cka")).strip().lower()
        exam_name = str(data.get("exam", "web-exam.yaml")).strip()
        if cert not in ("cka", "ckad", "cks"):
            return self._json({"error": "unknown cert"}, 400)
        if not exam_name.endswith(".yaml"):
            exam_name += ".yaml"
        exam_path = os.path.join(EXAMS_ROOT, cert, exam_name)
        if not os.path.exists(exam_path):
            return self._json({"error": f"exam not found: {cert}/{exam_name}"}, 404)
        try:
            STATE.load(cert=cert, exam_name=exam_name)
        except Exception as e:
            return self._json({"error": f"exam load failed: {e}"}, 500)
        STATE.started_at = None
        STATE.persist()
        return self._json({"ok": True, "cert": cert, "exam": exam_name,
                           "questions": len(STATE.questions)})

    def _api_db_reset(self, data):
        from cka_sim import db
        db.reset_all()
        STATE.started_at = None
        STATE.load()
        return self._json({"ok": True, "message": "Session reset — all results cleared"})

    def _import_db_bytes(self, raw: bytes):
        import tempfile
        from cka_sim import db
        if not raw:
            return self._json({"error": "empty file"}, 400)
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            db.import_db(tmp_path)  # validates + auto-repairs, raises ValueError
            STATE.load()
            return self._json({"ok": True,
                               "message": "Database imported (backup saved as .bak)",
                               "questions": len(STATE.questions)})
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:
            return self._json({"error": f"import failed: {e}"}, 500)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _api_db_upload(self, data):
        import base64
        b64 = data.get("data", "")
        if not b64:
            return self._json({"error": "no data provided"}, 400)
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return self._json({"error": "bad base64 data"}, 400)
        return self._import_db_bytes(raw)

    def _db_download(self):
        import base64
        from cka_sim import db
        db_path = db.export_db()
        if not os.path.exists(db_path):
            return self._json({"error": "no database yet"}, 404)
        with open(db_path, "rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode()
        self._json({"filename": "exam_state.db", "size": len(raw), "data": b64})

    def _db_info(self):
        from cka_sim import db
        db_path = db.export_db()
        if not os.path.exists(db_path):
            return self._json({"exists": False})
        size = os.path.getsize(db_path)
        sess = db.load_session()
        return self._json({"exists": True, "size": size, "path": db_path,
                           "session": {k: v for k, v in sess.items() if k != "started_at"}})


def main():
    ensure_kubeconfig()
    STATE.load()
    if not STATE.questions:
        print("no scenarios loaded for exam:", EXAM_FILE)
    print(f"cka-exam web server listening on :{PORT}  (exam: {EXAM_FILE})")
    print("terminal: real bash PTY served over WebSocket at /ws")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
