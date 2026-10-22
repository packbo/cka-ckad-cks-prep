# CKA / CKAD / CKS Simulator

A local Kubernetes exam trainer (à la Killercoda/Killer.sh) with a **progressive hint
system that teaches the *research method*** — the differentiator vs Killer.sh (which
has no hints).

Runs a real multi-node cluster via **kind**. One shared Python engine, **one bank
per certification**:

```
cka-sim/
├── scenarios/cka/...     today's bank (workloads, networking, storage, rbac...)
├── scenarios/ckad/       CKAD bank (same format)
├── scenarios/cks/        CKS bank (same format)
├── scenarios/ai/         🤖 AI-assisted Learning bank (live generation, web tab)
└── exams/cka|ckad|cks/   full-exam.yaml + web-exam.yaml per cert
```

## Quick start (from the repo root after git clone)

```bash
bash install.sh          # kind + deps (venv only if python is externally-managed:
                         #  Killercoda = system pip, Ubuntu 24 VPS = auto venv)
./run.sh list            # CKA bank (default)
./run.sh --cert ckad list  # once CKAD scenarios exist
./run.sh web             # browser exam UI on NodePort 30999
```

## Commands

| Command | Action |
|---------|--------|
| `./run.sh list` | List all scenarios (★ = tagged for review) |
| `./run.sh run <id>` | Run a single scenario |
| `./run.sh exam [--exam full-exam.yaml]` | Full timed exam with score report |
| `./run.sh tagged` | List scenarios tagged for review |
| `./run.sh review` | Re-run all tagged scenarios (revision queue) |
| `./run.sh tag <id> [--note "..."]` / `untag <id>` | Manage review tags from the shell |
| `./run.sh up` / `down` / `reset` | Manage the kind cluster |
| `./run.sh status` | Show tooling/cluster status |

## Web mode (Killercoda-style: questions left, real terminal right)

```bash
./run.sh web            # LOCAL server on :8080 (default) — ALL scenarios
                        # available (docker/node-exec: etcd, kubeadm, trivy…)
./run.sh web --pod      # alternative: deploy in-cluster (NodePort 30999)
                        # NB: node-exec scenarios are filtered in-pod
```

Split-pane page like the real Killercoda player: **questions + buttons on the
left, a real bash terminal (PTY over WebSocket, xterm.js) on the right** — the
divider is draggable (double-click resets, position saved). Tab-completion,
vim, Ctrl+C… all work in the web terminal.

Left-panel tabs:

| Tab | Content |
|-----|---------|
| **Exam** | Questions with hints (levels 1-4 + penalties), Check button (status `pending → active → done`), live score, per-domain report, session DB (download/import/reset) |
| **🤖 AI assisted Learning** | Exercises **generated live** by opencode/Claude in `scenarios/ai/` — hot-reloaded (no restart), with Check + scoring identical to the exam. Protocol: root `AGENTS.md` |
| **Cheatsheet** | All research methods: `paths(scalars)`, `explain --recursive`, list-vs-single, filters... |
| **Docs** | kubernetes.io links (allowed during the exam), each opening in a **new tab** |

How to open:

- **Default (local server)**: http://localhost:8080 — sur Killercoda, ouvrir
  l'onglet *Traffic Port* et saisir **8080** ; à distance `ssh -L 8080:localhost:8080`
- **--pod**: `http://<node-ip>:30999` (NodePort), puis `kubectl port-forward svc/cka-exam 8080:80`

On kind the exam server runs **in-cluster** (pod `cka-exam`, ServiceAccount
with broad RBAC — local training cluster only). Web exam = `exams/web-exam.yaml`
(`etcd-backup` stays CLI-only as it needs the host docker socket).
Re-running `./run.sh web` rebuilds the image and restarts the pod.

## Inside a scenario

You type **real kubectl commands** (pipes with `jq`/`grep` work), with **tab completion**
(kubectl-aware, via `kubectl __complete`), **exam aliases** (`k`, `kgp`, `$do`, `$now`...)
expanded automatically, and **persistent history** (up-arrow across sessions).
**Ctrl+C never skips the exercise** (terminal copy is safe) — only `:skip` moves on,
Ctrl+D leaves the session.
Meta-commands:

| Meta-command | Effect | Score penalty |
|--------------|--------|---------------|
| `:hint 1` | Orientation (which command family) | -10% |
| `:hint 2` | Research method (`paths(scalars)`, `explain --recursive`) | -25% |
| `:hint 3` | Doc tip / anti-pitfall | -40% |
| `:check [n]` | Validate the cluster state — current question, or question `n` from anywhere in the session (records the PASS if first) | — |
| `:cheat [topic]` | Speed cheatsheet: setup-once, jq, jsonpath, kubectl | — |
| `:tag [note]` / `:untag` | Mark scenario for review (persisted, `./run.sh review`) | — |
| `:back` / `:goto <n>` | In exam/review: previous question / jump (bare `:goto` = map) | — |
| `:exit` | Leave the session immediately (partial report) | — |
| `:solution` | Show full solution | 0 points |
| `:skip` / `:next` | Move on | — |

In sessions (`exam`/`review`), the first **PASSED** attempt is the one kept for the
score — revisiting a solved question is practice-only.

## Scenario format

`scenarios/<domain>/<id>/scenario.yaml` + `setup.yaml` (pre-existing resources):

```yaml
id: extract-image-deploy
title: "Find the configured image of a Deployment"
domain: workloads
weight: 3
difficulty: medium
setup:
  apply: setup.yaml
question: |
  What JSONPath gives the image configured in deployment "web"?
hints:
  - { level: 1, text: "Deployment -> .spec.template.spec.containers" }
  - { level: 2, text: "kubectl get deploy web -o json | jq -r 'paths(scalars)|join(\".\")' | grep image" }
check:
  assertions:
    - run: "kubectl get deploy web -o jsonpath='{.spec.template.spec.containers[0].image}'"
      contains: "nginx:1.21"
```

## Architecture (3 swappable layers)

```
Presentation : CLI (local)  ->  later: API + xterm.js
Engine       : engine, validator, hints, reporter, scenarios/   (unchanged when hosted)
Backend      : ClusterBackend interface
                |- KindBackend     (local, MVP)
                |- VclusterBackend (hosted, phase 2)
```

The engine and the scenario bank are **backend-agnostic**. Hosting the product later
only replaces the backend + presentation layers.

## Adding scenarios (any cert)

Create `scenarios/<cert>/<domain>/<id>/scenario.yaml` (+ optional `setup.yaml`) —
today everything lives under `scenarios/cka/`; drop CKAD/CKS banks in
`scenarios/ckad/`, `scenarios/cks/` (same format). Domains map to the exam
blueprints: `01-workloads`, `02-services-networking`, `03-storage`,
`04-cluster-architecture`, `05-troubleshooting`, `06-rbac`, `07-security` (CKS).
30 scenarios ship today (4 guided 00-basics: syntaxe kubectl + méthode explain) — many adapted from dgkanatsios/CKAD-exercises,
walidshaari CKA/CKS and the CNCF curriculum (see `../ressources/`).

Assertion keys: `run:` (shell command, stdout compared) or `file:` (path content),
with `contains:` or `equals:`.

Pick the bank with `./run.sh --cert cka|ckad|cks …` (or env `CKA_SIM_CERT`).
In-session navigation (`:back`, `:goto n`) **never resets** a question — your
changes are kept; `:reset` explicitly re-applies a scenario's setup.

## Official exam blueprints (checked 2026-10 — cncf/curriculum)

Questions are kept **terse on purpose** (exam style); details live in hints,
and assertions encode the grading.

**CKA v1.37** — 2h: Cluster Architecture, Installation & Configuration 25 ·
Workloads & Scheduling 15 · Services & Networking 20 · Storage 10 ·
Troubleshooting 30

**CKAD v1.37** — 2h: Application Design and Build 20 (incl. multi-container
pods: sidecar/init, volumes) · Application Deployment 20 (**blue/green,
canary**, rolling updates, Helm, Kustomize) · Application Observability and
Maintenance 15 · Application Environment, Configuration and Security 25 ·
Services and Networking 20

**CKS v1.34** (exam env v1.35, requires CKA) — 2h: Cluster Setup 15 ·
Cluster Hardening 15 · System Hardening 10 · Minimize Microservice
Vulnerabilities 20 · Supply Chain Security 20 · Monitoring, Logging and
Runtime Security 20

Sources: github.com/cncf/curriculum · training.linuxfoundation.org

## Two practice modes: solo (no AI) or with an AI tutor

### Solo — 100% offline, no AI involved

The simulator is fully standalone: pick your certification bank and train.

```bash
./run.sh --cert ckad list      # CKAD bank (27 scenarios today)
./run.sh --cert ckad exam      # timed 2h CKAD exam (18 questions), scored
./run.sh --cert ckad run canary-deploy
./run.sh --cert cka exam       # CKA bank
./run.sh --cert cks list       # CKS bank (to be filled)
./run.sh web                   # browser UI (NodePort 30999) — same banks
```

Nothing calls any AI: hints, scoring and checks all run locally against the
kind cluster.

### With an AI tutor (opencode / Claude Code / Cursor)

The repo ships `AGENTS.md` rules that turn the AI into an **examiner**:

1. Open a terminal and start a scenario solo (`./run.sh --cert ckad run blue-green-deploy`).
2. In the AI session, ask it to examine you *without giving the solution* — it
   follows the hint ladder (orientation → research method → near-solution).
3. The AI verifies your work **in the real cluster** (it can run kubectl) and
   corrects your *method*, not just the result.
4. It can also generate new scenarios (same format), then you validate them
   with `./run.sh run <id>` (see AGENTS.md workflow).

Rule of thumb: **solo mode grades you, AI mode teaches you.**
