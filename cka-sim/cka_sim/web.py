"""Web exam server.

Serves the exam UI (questions, hints, checks, terminal box) plus a Cheatsheet
tab (research methods from data/cheatsheet.json) and a Docs tab with
kubernetes.io links (opened in a new tab).

Run in-cluster (deployed by ./run.sh web) and access via:
    kubectl port-forward svc/cka-exam 8080:80   ->   http://localhost:8080
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
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

DOC_LINKS = [
    ("kubectl Cheat Sheet", "https://kubernetes.io/docs/reference/kubectl/cheatsheet/"),
    ("JSONPath reference", "https://kubernetes.io/docs/reference/kubectl/jsonpath/"),
    ("Pods", "https://kubernetes.io/docs/concepts/workloads/pods/"),
    ("Deployments", "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"),
    ("Services", "https://kubernetes.io/docs/concepts/services-networking/service/"),
    ("Network Policies", "https://kubernetes.io/docs/concepts/services-networking/network-policies/"),
    ("Persistent Volumes", "https://kubernetes.io/docs/concepts/storage/persistent-volumes/"),
    ("ConfigMaps", "https://kubernetes.io/docs/concepts/configuration/configmap/"),
    ("Secrets", "https://kubernetes.io/docs/concepts/configuration/secret/"),
    ("RBAC", "https://kubernetes.io/docs/reference/access-authn-authz/rbac/"),
    ("kubeadm upgrade", "https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/"),
    ("etcd backup/restore", "https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/"),
    ("kubectl shell autocompletion", "https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#enable-shell-autocompletion"),
    ("helm completion", "https://helm.sh/docs/helm/helm_completion/"),
]


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
            # restore per-question state
            prev = saved.get(sid, {})
            self.questions.append({
                "scenario": s,
                "status": prev.get("status", "pending"),
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


def load_cheatsheet() -> dict:
    try:
        with open(CHEATSHEET_PATH) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {"research_methods": []}


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
    """Real shell completion via the hidden cobra `__complete` protocol.

    Returns suggestions for the word being typed: subcommands, flags
    (options), resource types and even live resource names.
    """
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
            "note": f"'{first}' is not installed in this sandbox — activation "
                    f"commands for your own shell are in the Cheatsheet tab.",
        }
    tool = TOOL_MAP.get(first)
    if tool is None:
        return {
            "suggestions": [],
            "note": "Tab completion here covers: kubectl / k. "
                    "Activation for helm, kubeadm & co: Cheatsheet tab.",
        }
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


# ------------------------------------------------------------------- UI ----
def build_html() -> str:
    docs_li = "\n".join(
        f'<li><a href="{url}" target="_blank" rel="noopener">{name} &#8599;</a></li>'
        for name, url in DOC_LINKS
    )
    return HTML_TEMPLATE.replace("__DOCS__", docs_li)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CKA Exam Simulator</title>
<style>
  :root{--bg:#0f1420;--panel:#1a2233;--panel2:#141b2b;--txt:#dde5f2;--mut:#8b99b0;
        --acc:#4da3ff;--ok:#3ecf8e;--bad:#ff6b6b;--hint:#c58aff;--line:#28324a}
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--txt)}
  header{display:flex;align-items:center;gap:18px;padding:12px 20px;background:var(--panel);border-bottom:1px solid var(--line)}
  header h1{font-size:17px;margin:0;color:var(--acc)}
  .tabs{display:flex;gap:4px;margin-left:auto}
  .tab{padding:7px 16px;border-radius:8px 8px 0 0;cursor:pointer;background:transparent;color:var(--mut);border:1px solid transparent;font-size:14px}
  .tab.active{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-bottom-color:var(--panel2)}
  #timer{font-family:ui-monospace,monospace;font-size:16px;color:var(--acc)}
  main{max-width:1180px;margin:0 auto;padding:18px}
  .page{display:none}.page.active{display:block}
  .grid{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}
  @media(max-width:960px){.grid{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
  .card h3{margin:0 0 10px;font-size:14px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
  .meta{color:var(--mut);font-size:13px;margin-bottom:8px}
  .qtext{white-space:pre-wrap;font-size:15px;line-height:1.55;background:var(--panel2);
         border:1px solid var(--line);border-radius:8px;padding:14px;margin:8px 0}
  button{background:var(--acc);border:0;color:#08121f;font-weight:600;padding:8px 14px;
         border-radius:7px;cursor:pointer;font-size:13px;margin:3px 6px 3px 0}
  button:hover{filter:brightness(1.12)}
  button.ghost{background:transparent;color:var(--txt);border:1px solid var(--line)}
  button.warn{background:var(--hint);color:#1d1226}
  button.ok{background:var(--ok)}
  input.cmd{width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--txt);
            border-radius:7px;padding:10px 12px;font-family:ui-monospace,monospace;font-size:13px}
  pre{background:#0b101c;border:1px solid var(--line);border-radius:8px;padding:12px;
      overflow:auto;font-size:12.5px;max-height:340px;white-space:pre-wrap;word-break:break-word}
  .hintbox{border-left:3px solid var(--hint);padding:8px 12px;margin:8px 0;background:var(--panel2);border-radius:0 8px 8px 0;white-space:pre-wrap;font-size:14px}
  .res-ok{color:var(--ok)}.res-bad{color:var(--bad)}
  .qtable{width:100%;border-collapse:collapse;font-size:13.5px}
  .qtable td,.qtable th{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left}
  .st-solved{color:var(--ok)}.st-skipped{color:var(--mut)}.st-active{color:var(--acc)}
  .st-pending{color:var(--mut)}.st-failed{color:var(--bad)}
  .cheat{border-left:3px solid var(--acc);padding:10px 14px;margin:10px 0;background:var(--panel2);border-radius:0 8px 8px 0}
  .cheat .need{font-weight:700;margin-bottom:6px}
  .cheat code{display:block;background:#0b101c;border:1px solid var(--line);border-radius:6px;
              padding:8px 10px;margin:6px 0;font-size:12.5px;white-space:pre-wrap;word-break:break-word}
  .cheat .note{color:var(--mut);font-size:13px}
  .docs ul{list-style:none;padding:0}
  .docs li{padding:9px 0;border-bottom:1px solid var(--line)}
  .docs a{color:var(--acc);text-decoration:none;font-size:15px}
  .docs a:hover{text-decoration:underline}
  .certbtn{background:transparent;border:1px solid var(--line);color:var(--mut);padding:4px 10px;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600}
  .certbtn.active{background:var(--acc);color:#08121f;border-color:var(--acc)}
  .certbtn:hover:not(.active){color:var(--txt);border-color:var(--acc)}
  .suggbox{position:relative;margin-top:6px;max-height:200px;overflow:auto;background:#0b101c;
           border:1px solid var(--line);border-radius:8px;display:none}
  .suggbox.show{display:block}
  .sg{padding:6px 12px;font-family:ui-monospace,monospace;font-size:12.5px;cursor:pointer;color:var(--txt)}
  .sg:hover,.sg.on{background:var(--panel2);color:var(--acc)}
  .sgmeta{padding:5px 12px;color:var(--mut);font-size:12px}
  .bigscore{font-size:42px;font-weight:800}
  #banner{display:none;background:var(--panel);border:1px solid var(--line);border-radius:10px;
          padding:18px;margin-bottom:16px}
</style>
</head>
<body>
<header>
  <h1>CKA Exam Simulator</h1>
  <span id="portchip" title="NodePort to enter in the traffic-port tab" style="display:none;background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:4px 10px;font-family:ui-monospace,monospace;color:var(--ok);font-size:14px"></span>
  <span id="certbar" style="display:flex;gap:4px;align-items:center">
    <button id="cert-cka" class="certbtn active" onclick="switchCert('cka')">CKA</button>
    <button id="cert-ckad" class="certbtn" onclick="switchCert('ckad')">CKAD</button>
    <button id="cert-cks" class="certbtn" onclick="switchCert('cks')">CKS</button>
    <select id="examselect" onchange="switchExam(this.value)" style="background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:5px;padding:4px 8px;font-size:13px"></select>
  </span>
  <span id="hscore" style="color:var(--mut);font-size:14px"></span>
  <span id="timer">--:--</span>
  <nav class="tabs">
    <div class="tab active" data-p="p-exam">Exam</div>
    <div class="tab" data-p="p-cheat">Cheatsheet &amp; Hints</div>
    <div class="tab" data-p="p-docs">Docs</div>
    <div class="tab" data-p="p-access">Access</div>
  </nav>
</header>
<main>

<section id="p-exam" class="page active">
  <div id="banner" class="card"></div>
  <div class="grid">
    <div>
      <div class="card" id="qcard">
        <h3>Question</h3>
        <div id="qbody"><div class="meta">Press &laquo; Start question &raquo; to begin.</div></div>
      </div>
      <div class="card">
        <h3>Questions</h3>
        <table class="qtable" id="qtable"></table>
        <div style="margin-top:10px">
          <button class="ghost" onclick="showReport()">Refresh report</button>
        </div>
      </div>
    </div>
    <div>
      <div class="card">
        <h3>Terminal</h3>
        <input class="cmd" id="cmd" placeholder="kubectl get pods -A   (Tab = completion, Enter = run)" spellcheck="false">
        <div id="sugg" class="suggbox"></div>
        <button onclick="runCmd()">Run</button>
        <button class="ghost" onclick="clearOut()">Clear</button>
        <span class="meta" style="margin-left:6px">Tab: kubectl completion (commands, flags, resources, names)</span>
        <pre id="out"></pre>
      </div>
      <div class="card">
        <h3>Report</h3>
        <div id="report" class="meta">Start the exam to see the report.</div>
      </div>
    </div>
  </div>
</section>

<section id="p-cheat" class="page">
  <div class="card">
    <h3>Research methods &mdash; how to find anything</h3>
    <div class="meta">The exam grades cluster state, not the path. These methods find any field, path or manifest.</div>
    <div id="cheats"></div>
  </div>
</section>

<section id="p-docs" class="page docs">
  <div class="card">
    <h3>kubernetes.io &mdash; allowed during the exam</h3>
    <div class="meta">Links open in a new tab. Use Ctrl+F inside a page to jump to the example you need.</div>
    <ul>
__DOCS__
    </ul>
  </div>
</section>

<section id="p-access" class="page">
  <div class="card">
    <h3>How to open this UI &mdash; traffic port</h3>
    <div id="accessbox" class="meta">Loading...</div>
  </div>
</section>

</main>
<script>
let CUR=-1;
const $=id=>document.getElementById(id);

document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');$(t.dataset.p).classList.add('active');
}));

async function api(path,body){
  const r=await fetch('/api/'+path,{method:body?'POST':'GET',
    headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  return r.json();
}

async function refresh(){const s=await api('state');renderState(s);}
function renderState(s){
  if(s.advisory){showBanner('⚠ '+s.advisory);}
  let got=0,max=0;
  const rows=s.questions.map(q=>{got+=q.score;max+=q.weight;
    return `<tr style="cursor:pointer" onclick="loadQ(${q.index})">
      <td>${q.index+1}</td><td>${q.id}</td><td>${q.domain}</td>
      <td class="st-${q.status}">${q.status}</td>
      <td>${q.score}/${q.weight}</td><td>${q.hints_used||'-'}</td></tr>`;}).join('');
  $('qtable').innerHTML='<tr><th>#</th><th>id</th><th>domain</th><th>status</th><th>score</th><th>hints</th></tr>'+rows;
  $('hscore').textContent=`score ${got.toFixed(1)} / ${max}`;
  window.EXAM_MIN=s.minutes;window.ELAPSED=s.elapsed;
}
setInterval(()=>{if(window.EXAM_MIN===undefined)return;
  const left=Math.max(0,window.EXAM_MIN*60-window.ELAPSED);window.ELAPSED+=1;
  if(left<=0){$('timer').textContent='00:00';return;}
  const h=Math.floor(left/3600),m=Math.floor(left%3600/60),s2=left%60;
  $('timer').textContent=(h?h+':':'')+String(m).padStart(2,'0')+':'+String(s2).padStart(2,'0');
},1000);

async function loadQ(i){
  const s=await api('state');const q=s.questions[i];if(!q)return;
  CUR=i;
  $('qbody').innerHTML=`<div class="meta">${q.domain} &middot; weight ${q.weight}% &middot; ${q.difficulty} &middot; status: <span class="st-${q.status}">${q.status}</span></div>
   <div class="qtext" id="qtext">Press Start to load the question and its setup.</div>
   <div id="hints"></div>
   <div style="margin-top:10px">
     <button class="ok" onclick="startQ(${i})">Start question</button>
     <button class="warn" onclick="askHint(1)">Hint 1 (-10%)</button>
     <button class="warn" onclick="askHint(2)">Hint 2 (-25%)</button>
     <button class="warn" onclick="askHint(3)">Hint 3 (-40%)</button>
     <button class="ghost" onclick="askHint(4)">Solution (0%)</button>
     <button class="ok" onclick="checkQ()">Check</button>
     <button class="ghost" onclick="skipQ()">Skip</button>
     <button class="ghost" id="tagbtn" onclick="tagQ()">★ Tag</button>
     <button class="ghost" onclick="resetQ()">↻ Reset</button>
   </div>`;
  if(q.status!=='pending'){const d=await api('question',{index:i});
    $('qtext').textContent=d.question;
    if(d.hint_logs) d.hint_logs.forEach(h=>addHintBox(h));}
}
async function startQ(i){
  const d=await api('start',{index:i});
  $('qtext').textContent=d.question;$('hints').innerHTML='';
  out('');refresh();
}
async function askHint(level){
  if(CUR<0)return;const d=await api('hint',{index:CUR,level});
  addHintBox(d.text);refresh();
}
function addHintBox(t){const div=document.createElement('div');div.className='hintbox';
  div.textContent=t;$('hints').appendChild(div);}
async function checkQ(){
  if(CUR<0)return;const d=await api('check',{index:CUR});
  const lines=d.results.map(r=>`<div class="${r.passed?'res-ok':'res-bad'}">${r.passed?'PASS':'FAIL'} &mdash; ${r.detail}</div>`).join('');
  $('hints').innerHTML+='<div class="hintbox">'+lines+`<div><b>${d.passed?'SOLVED':'Not yet'}</b> &mdash; score ${d.score}/${d.weight}</div></div>`;
  if(d.passed){showBanner(`SOLVED &mdash; ${d.score}/${d.weight} points`);}
  refresh();showReport();
}
async function skipQ(){
  if(CUR<0)return;await api('skip',{index:CUR});refresh();showReport();
}
async function tagQ(){
  if(CUR<0)return;const d=await api('tag',{index:CUR});
  $('tagbtn').textContent=d.tagged?'★ Tagged':'★ Tag';
  refresh();
}
async function resetQ(){
  if(CUR<0)return;const d=await api('reset',{index:CUR});
  if(d.question){$('qtext').textContent=d.question;$('hints').innerHTML='';}
  showBanner('Scenario reset');refresh();
}
async function switchCert(cert){
  document.querySelectorAll('.certbtn').forEach(b=>b.classList.remove('active'));
  $('cert-'+cert).classList.add('active');
  const d=await api('cert',{cert,exam:'web-exam.yaml'});
  showBanner(`Loaded ${cert.toUpperCase()} exam — ${d.questions} questions`);
  refresh();showReport();
}
async function switchExam(name){
  const cert=$('cert-cka').classList.contains('active')?'cka':
    $('cert-ckad').classList.contains('active')?'ckad':'cks';
  const d=await api('cert',{cert,exam:name});
  showBanner(`Loaded ${cert.toUpperCase()} / ${name} — ${d.questions} questions`);
  refresh();showReport();
}
async function loadExams(){
  try{
    const d=await api('exams');
    const sel=$('examselect');
    sel.innerHTML='<option value="">— exam —</option>';
    (d.exams||[]).forEach(e=>{
      const o=document.createElement('option');
      o.value=e.name;o.textContent=`${e.cert}/${e.name}`;
      sel.appendChild(o);
    });
  }catch(e){console.warn('exams list failed',e)}
}

// ── Startup modal ──
let MODAL=null;
function showStartModal(){
  if(MODAL)MODAL.remove();
  MODAL=document.createElement('div');
  MODAL.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:999';
  MODAL.innerHTML=`<div style="background:var(--panel);border:1px solid var(--acc);border-radius:12px;padding:32px;min-width:340px;text-align:center">
    <h2 style="margin:0 0 20px;color:var(--acc)">🎓 Exam Simulator</h2>
    <div style="margin-bottom:16px">
      <div style="color:var(--mut);font-size:13px;margin-bottom:8px">Certification</div>
      <div style="display:flex;gap:8px;justify-content:center">
        <button class="certbtn active" id="modal-cka" onclick="modalCert('cka')">CKA</button>
        <button class="certbtn" id="modal-ckad" onclick="modalCert('ckad')">CKAD</button>
        <button class="certbtn" id="modal-cks" onclick="modalCert('cks')">CKS</button>
      </div>
    </div>
    <div style="margin-bottom:24px">
      <div style="color:var(--mut);font-size:13px;margin-bottom:8px">Exam</div>
      <select id="modal-exam" onchange="void 0" style="background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:8px 16px;font-size:14px;width:200px">
        <option value="web-exam.yaml">web-exam (recommended)</option>
        <option value="full-exam.yaml">full-exam (all questions)</option>
      </select>
    </div>
    <button class="ok" style="padding:10px 32px;font-size:15px" onclick="startExam()">Start</button>
  </div>`;
  document.body.appendChild(MODAL);
}
let MODAL_CERT='cka';
function modalCert(c){
  MODAL_CERT=c;
  document.querySelectorAll('[id^="modal-"]').forEach(b=>b.classList.remove('active'));
  const btn=document.getElementById('modal-'+c);if(btn)btn.classList.add('active');
}
async function startExam(){
  const exam=$('modal-exam')?$('modal-exam').value:'web-exam.yaml';
  if(MODAL){MODAL.remove();MODAL=null;}
  document.querySelectorAll('.certbtn').forEach(b=>b.classList.remove('active'));
  const hb=document.querySelector('.header .certbtn#cert-'+MODAL_CERT);if(hb)hb.classList.add('active');
  const d=await api('cert',{cert:MODAL_CERT,exam});
  showBanner(`${MODAL_CERT.toUpperCase()} / ${exam} — ${d.questions} questions loaded`);
  refresh();showReport();loadExams();
}
async function runCmd(){
  const c=$('cmd').value.trim();if(!c)return;
  const d=await api('cmd',{command:c});
  out((d.stdout||'')+(d.stderr?(d.stderr:''):'')+(d.rc?`\n[exit ${d.rc}]`:''));
}
function out(t){$('out').textContent=t||' ';}
function clearOut(){out('');}

let SG={items:[],idx:-1};
function sgHide(){$('sugg').classList.remove('show');$('sugg').innerHTML='';SG={items:[],idx:-1};}
function sgRender(note){
  const box=$('sugg');
  if(!SG.items.length){box.classList.add('show');box.innerHTML=`<div class="sgmeta">${note||'no completion'}</div>`;return;}
  box.classList.add('show');
  box.innerHTML=SG.items.map((s,i)=>`<div class="sg${i===SG.idx?' on':''}" onclick="sgPick(${i})">${s.replace(/\t/g,' — ')}</div>`).join('')
    +(note?`<div class="sgmeta">${note}</div>`:'');
  const on=box.querySelector('.sg.on');if(on)on.scrollIntoView({block:'nearest'});
}
function sgPick(i){
  const s=SG.items[i];if(s===undefined)return;
  const v=$('cmd').value;
  const parts=v.trimStart().split(/\s+/);
  if(v.endsWith(' '))parts.push('');
  parts[parts.length-1]=s.split('\t')[0];
  $('cmd').value=parts.join(' ');
  sgHide();$('cmd').focus();
}
async function sgFetch(){
  const d=await api('complete',{input:$('cmd').value});
  SG={items:d.suggestions||[],idx:-1};sgRender(d.note);
}
$('cmd').addEventListener('keydown',async e=>{
  if(e.key==='Enter'){sgHide();runCmd();return;}
  if(e.key==='Escape'){sgHide();return;}
  if(e.key==='Tab'){e.preventDefault();
    if(!SG.items.length){await sgFetch();}
    if(SG.items.length){SG.idx=(SG.idx+1)%SG.items.length;sgRender();}
    return;}
  if((e.key==='ArrowDown'||e.key==='ArrowUp')&&SG.items.length){
    e.preventDefault();
    const n=SG.items.length;
    SG.idx=e.key==='ArrowDown'?(SG.idx+1)%n:(SG.idx-1+n)%n;
    sgRender();}
});
$('cmd').addEventListener('input',()=>{if(SG.items.length)sgHide();});

async function showReport(){
  const d=await api('report');
  const dom=d.domains.map(x=>`<tr><td>${x.domain}</td><td>${x.score.toFixed(1)}</td><td>${x.max}</td></tr>`).join('');
  const qs=d.questions.map(q=>`<tr><td>${q.id}</td><td class="st-${q.status}">${q.status}</td><td>${q.score}/${q.weight}</td><td>${q.hints||'-'}</td></tr>`).join('');
  $('report').innerHTML=`<div class="bigscore" style="color:${d.passed?'var(--ok)':'var(--bad)'}">${d.percent}%</div>
   <div class="meta">${d.earned.toFixed(1)} / ${d.total} points &middot; threshold ${d.threshold}% &middot; ${d.passed?'PASS':'BELOW PASS'}</div>
   <table class="qtable"><tr><th>domain</th><th>score</th><th>max</th></tr>${dom}</table>
   <table class="qtable" style="margin-top:10px"><tr><th>question</th><th>status</th><th>score</th><th>hints</th></tr>${qs}</table>`;
}
function showBanner(t){$('banner').style.display='block';$('banner').innerHTML=`<div style="font-size:20px;font-weight:700">${t}</div>`;}

async function loadCheats(){
  const d=await api('cheatsheet');
  $('cheats').innerHTML=(d.research_methods||[]).map(c=>
   `<div class="cheat"><div class="need">${c.need}</div><code>${c.how}</code><div class="note">${c.note}</div></div>`).join('');
}
async function loadAccess(){
  try{
    const d=await api('access');
    if(d.nodePort){$('portchip').style.display='inline-block';$('portchip').textContent='port '+d.nodePort;}
    const ips=(d.nodeIPs||[]).map(ip=>`<li><code>http://${ip}:${d.nodePort}</code></li>`).join('');
    $('accessbox').innerHTML=`
      <div style="font-size:34px;font-weight:800;color:var(--ok);font-family:ui-monospace,monospace">${d.nodePort}</div>
      <div class="meta">Service <code>cka-exam</code> is exposed as <b>NodePort</b> (any port 30000&ndash;32767 works this way).</div>
      <div class="cheat"><div class="need">On Killercoda</div>
        Open the <b>Traffic Port</b> tab (right of the Terminal tab), enter <b>${d.nodePort}</b> and confirm &mdash;
        the page is then served at <code>https://&lt;session-id&gt;-${d.nodePort}.&lt;your-env-domain&gt;</code>.</div>
      <div class="cheat"><div class="need">On this local kind cluster</div>
        Open any node IP at that port in your browser:<ul style="margin:8px 0 0 18px">${ips}</ul>
        <div class="note">Node IPs are Docker bridges, reachable from the Linux host.</div></div>
      <div class="cheat"><div class="need">Fallback (port-forward)</div>
        <code>kubectl port-forward svc/cka-exam 8080:80</code> then open <code>http://localhost:8080</code>.</div>`;
  }catch(e){$('accessbox').textContent='access info unavailable: '+e;}
}
refresh();loadCheats();loadAccess();loadExams();showStartModal();
</script>
</body>
</html>
"""


# --------------------------------------------------------------- handler --
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self):
        """Serve the static index.html from cka_sim/static/."""
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "static"
        html_file = static_dir / "index.html"
        if not html_file.exists():
            self._html("<h1>cka-sim web</h1><p>static/index.html not found</p>")
            return
        body = html_file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text):
        body = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_static()
        elif self.path == "/api/state":
            self._json(STATE.public())
        elif self.path == "/api/report":
            self._json(STATE.report())
        elif self.path == "/api/cheatsheet":
            self._json(load_cheatsheet())
        elif self.path == "/api/access":
            self._json(access_info())
        elif self.path == "/api/exams":
            self._json({"exams": available_exams()})
        elif self.path == "/api/db/download":
            self._db_download()
        elif self.path == "/api/db/info":
            self._db_info()
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)

        p = self.path.replace("/api/", "")
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
        if s.setup_fullpath and os.path.exists(s.setup_fullpath):
            run_shell(f"kubectl apply -f {s.setup_fullpath}")
        q["status"] = "active"
        from cka_sim import env as _env
        return self._json({"ok": True, "question": _env.substitute(s.question)})

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
        if passed and q["status"] != "solved":
            STATE.persist()  # save to SQLite
            pen = PENALTY.get(q["hints_used"], 0.0) if q["hints_used"] < 4 else 1.0
            q["score"] = round(max(0.0, s.weight * (1.0 - pen)), 2)
            q["status"] = "solved"
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
        if q["status"] != "solved":
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
        if sp and os.path.exists(sp):
            run_shell(f"kubectl delete -f {sp} --ignore-not-found --wait=true --timeout=30s", timeout=60)
            run_shell(f"kubectl apply -f {sp}")
        q["status"] = "pending"
        q["hints_used"] = 0
        from cka_sim import env as _env
        return self._json({"ok": True, "question": _env.substitute(s.question)})

    def _api_cert(self, data):
        cert = str(data.get("cert", "cka")).strip().lower()
        exam_name = str(data.get("exam", "web-exam.yaml")).strip()
        if cert not in ("cka", "ckad", "cks"):
            return self._json({"error": "unknown cert"}, 400)
        STATE.load(cert=cert, exam_name=exam_name)
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

    def _api_db_upload(self, data):
        import base64
        import tempfile
        from cka_sim import db
        b64 = data.get("data", "")
        if not b64:
            return self._json({"error": "no data provided"}, 400)
        try:
            raw = base64.b64decode(b64)
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            db.import_db(tmp_path)
            os.unlink(tmp_path)
            STATE.load()
            return self._json({"ok": True, "message": "Database imported",
                               "questions": len(STATE.questions)})
        except Exception as e:
            return self._json({"error": str(e)}, 400)

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
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
