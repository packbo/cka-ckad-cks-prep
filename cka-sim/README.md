# CKA Simulator

A local Kubernetes exam trainer (à la Killercoda/Killer.sh) with a **progressive hint
system that teaches the *research method*** — the differentiator vs Killer.sh (which
has no hints).

Runs a real multi-node cluster via **kind**. Built in Python, with a clean
`ClusterBackend` abstraction so it can later evolve into a hosted SaaS (vcluster
Private Nodes) without touching the scenario engine.

## Quick start

```bash
bash install.sh          # installs kind + jq + python deps + creates the cluster
./run.sh list            # list scenarios (no cluster needed)
./run.sh status          # cluster / tooling status
./run.sh run create-deploy       # run one scenario
./run.sh exam            # full timed exam (2h, weighted, scored)
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

## Inside a scenario

You type **real kubectl commands** (pipes with `jq`/`grep` work), with **tab completion**
(kubectl-aware, via `kubectl __complete`), **exam aliases** (`k`, `kgp`, `$do`, `$now`...)
expanded automatically, and **persistent history** (up-arrow across sessions).
Meta-commands:

| Meta-command | Effect | Score penalty |
|--------------|--------|---------------|
| `:hint 1` | Orientation (which command family) | -10% |
| `:hint 2` | Research method (`paths(scalars)`, `explain --recursive`) | -25% |
| `:hint 3` | Doc tip / anti-pitfall | -40% |
| `:check` | Validate the cluster state | — |
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

## Adding scenarios

Create `scenarios/<domain>/<id>/scenario.yaml` (+ optional `setup.yaml`). Domains map to
the exams: `01-workloads`, `02-services-networking`, `03-storage`,
`04-cluster-architecture`, `05-troubleshooting`, `06-rbac`, `07-security` (CKS).
29 scenarios ship today (3 guided 00-basics for kubectl syntax beginners) — many adapted from dgkanatsios/CKAD-exercises,
walidshaari CKA/CKS and the CNCF curriculum (see `../ressources/`).

Assertion keys: `run:` (shell command, stdout compared) or `file:` (path content),
with `contains:` or `equals:`.
