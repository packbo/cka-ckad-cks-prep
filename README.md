# CKA / CKAD / CKS — Trainer complet (simulateur + IA + web UI)

Tout ce qu'il faut pour préparer les certifications Kubernetes **CNCF** :
**100+ scénarios** testés sur vrai cluster, **examens chronométrés notés**,
**UI web façon examen CKA** (questions à gauche, vrai terminal à droite) et
**exercices générés en direct par IA** (opencode/Claude).

> Repo : https://github.com/packbo/cka-ckad-cks-prep
> Déployable en **1 commande** sur Killercoda ou tout serveur Ubuntu.
> Prêt pour l'IA : `AGENTS.md` transforme opencode/Claude en examinateur
> (indices progressifs, génération d'exercices live).

---

## Démarrage rapide

### Option A — Killercoda / serveur avec cluster Kubernetes préinstallé

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/bootstrap.sh)
```

À la fin de l'installation, l'UI web démarre **automatiquement en arrière-plan**
et le terminal affiche :

```
───────────────────────────────────────────────────────────────
 🎓  WEB EXAM UI READY — running in the background on :8080
 ➜  Open the "Traffic Port" tab (top bar, right of "Terminal")
    and enter the port:   8080
───────────────────────────────────────────────────────────────
```

Sur **Killercoda** : ouvrir l'onglet **Traffic Port** (à droite de l'onglet
Terminal) et saisir **8080**. La page d'examen s'ouvre.

### Option B — Machine vierge (sans cluster) : docker + kind

```bash
git clone https://github.com/packbo/cka-ckad-cks-prep.git
cd cka-ckad-cks-prep/cka-sim
bash install.sh
```

`install.sh` détecte l'absence de cluster, installe **kind** et crée un cluster
**1 control-plane + 2 workers** (docker requis), puis démarre l'UI web en
arrière-plan (**NodePort 30999**) et affiche l'URL à ouvrir :

```
🎓  WEB EXAM UI READY — NodePort 30999
➜  on this host     :  http://172.18.0.2:30999
➜  from your browser:  http://<public-ip>:30999   (open the firewall)
    fallback          :  kubectl port-forward svc/cka-exam 8080:80
```

### Option C — Cluster existant (GKE / EKS / kubeadm…)

`install.sh` le détecte tout seul : rien à installer, l'UI web tourne en local
sur **http://localhost:8080** avec votre contexte kubectl courant
(tunnel SSH si distant : `ssh -L 8080:localhost:8080 <host>`).

---

## L'UI Web (`./run.sh web`)

Page façon **Killercoda / examen CKA réel** :

| Zone | Contenu |
|---|---|
| **Panneau gauche** | onglets Exam · 🤖 AI assisted Learning · Cheatsheet · Docs, question courante, boutons (Hint 1-3, Solution, **Check**, Skip, Tag, Reset, Pause), liste des questions, rapport, session SQLite (download/import/reset) |
| **Panneau droit** | **vrai terminal bash** (PTY complet via WebSocket) : Tab-complétion kubectl, vim, Ctrl+C, historique — tout fonctionne |
| **Séparateur central** | glisser pour redimensionner gauche ⇄ droite (double-clic = reset, position mémorisée) |

Barre du haut : sélecteur **CKA / CKAD / CKS**, choix de l'examen, score, timer.

### Onglet « AI assisted Learning »

Les exercices **générés en direct par l'IA** (opencode) apparaissent ici
automatiquement (hot-reload toutes les 15 s, aucun restart). Bouton **Check**
et **scoring** identiques à l'onglet Exam (`pending → active → done`).

Demander par exemple dans une session opencode : *« un exercice NetworkPolicy
avec un piège sur les namespaces »* — l'IA écrit
`cka-sim/scenarios/ai/ai-netpol-1/scenario.yaml`, teste les assertions via
l'API, puis l'exercice s'affiche dans l'onglet. Voir `AGENTS.md` § *AI
assisted Learning* pour le protocole complet.

---

## Toutes les commandes

Entry points à la **racine du dépôt** (dispatchent vers `cka-sim/`) :

```bash
./run.sh list                     # banque de scénarios (CKA par défaut)
./run.sh --cert ckad list         # banque CKAD
./run.sh --cert cks list          # banque CKS
./run.sh list --domain storage    # filtrer par domaine (workloads, rbac, network…)
./run.sh run <id>                 # lancer un scénario (ex: ./run.sh run create-deploy)
./run.sh exam                     # examen complet chronométré (2h, noté, seuil 66%)
./run.sh exam --exam web-exam     # variante plus courte (fichier exams/<cert>/)
./run.sh review                   # rejouer les scénarios taggés ★
./run.sh tag <id> [--note "..."]  # tagger pour révision
./run.sh untag <id>               # retirer le tag
./run.sh web                      # (re)démarrer l'UI web
./run.sh webstop                  # arrêter l'UI web
./run.sh status                   # état cluster/outils/contexte
./run.sh up | down | reset        # cycle de vie du cluster kind (option B/C)
./install.sh                      # setup complet (+ auto-start web)
```

Identique directement dans `cka-sim/` : `./run.sh …`, `./run.sh status`, …

### Commandes en session (`./run.sh run` / `exam`)

| Commande | Effet |
|---|---|
| `:hint <1-4>` | indice progressif (1 orientation → 3 quasi-solution, 4 = solution) |
| `:check` / `:check <n>` | valider la question courante / une autre question |
| `:cheat` / `:cheatsheet` | anti-cheat de recherche |
| `:question` | réafficher l'énoncé |
| `:reset` | ré-appliquer le setup (état vierge) |
| `:back` / `:goto <n>` | naviguer **sans perdre le travail** |
| `:solution` | solution complète |
| `:skip` / `:next` | passer / question suivante |
| `:tag` / `:untag` | marquer pour révision |
| `:exit` / `:quit` | quitter (rapport partiel) |

`Ctrl+C` n'interrompt plus l'exercice ; `:skip` ou `Ctrl+D` restent les sorties.

### Scoring

- Question validée sans indice : 100 % des points (`weight`)
- Hint 1 : **-10 %** · Hint 2 : **-25 %** · Hint 3 : **-40 %** · Solution : **0 %**
- Examen réussi à **66 %** (67 % CKS) — comme le vrai examen
- Status web : `pending → active → done` (validé) ou `skipped` ;
  une question validée **reste `done`** même si on la re-clique.

---

## Variables d'environnement & options d'installation

| Variable | Défaut | Rôle |
|---|---|---|
| `CKA_SIM_CLUSTER` | `cka-sim` | nom du cluster kind (option B) |
| `CKA_SIM_WEB_PORT` | `8080` | port de l'UI web (cluster préinstallé / port-forward) |
| `CKA_SIM_VENV` | `auto` | `force` / `never` / `auto` (venv si python externally-managed) |
| `CKA_SIM_CERT` | `cka` | banque par défaut |
| `CKA_SIM_DB` | `data/exam_state.db` | chemin de la base SQLite |

```bash
bash install.sh --venv        # forcer un venv python
bash install.sh --no-venv     # installer system-wide (Killercoda)
CKA_SIM_WEB_PORT=9090 ./run.sh web
```

`install.sh` installe aussi (best-effort) : `kubectl`, `kind` (si besoin),
`jq`, `metrics-server` (HPA/kubectl top), **GitHub CLI (`gh`)**, puis
**démarre l'UI web en arrière-plan** et affiche le port/URL à ouvrir
(message adapté : Killercoda ⇒ Traffic Port 8080, kind ⇒ NodePort 30999).

---

## Format d'un scénario

`cka-sim/scenarios/<cert>/<domaine>/<id>/scenario.yaml` :

```yaml
id: extract-image-deploy
title: "Extraire l'image d'un Deployment"
domain: workloads          # 00-basics…06-rbac
weight: 3
difficulty: medium
requires: {workers: 1}     # optionnel : filtré si cluster trop petit
setup:
  apply: setup.yaml        # ressources pré-créées (optionnel)
question: |
  ...
hints:
  - { level: 1, text: "orientation : famille de commandes" }
  - { level: 2, text: "méthode : jq paths(scalars) / kubectl explain --recursive" }
  - { level: 3, text: "piège / astuce doc" }
check:
  assertions:
    - run: "kubectl get deploy web -o jsonpath='{.spec.template.spec.containers[0].image}'"
      contains: "nginx:1.21"
```

Placeholders substitués automatiquement : `%CP%`, `%WORKER%`, `%WORKER2%`,
`%NODEEXEC%`, `%CPCP%`, `%CPDEST%`, `%AUDITLOG%`.

Banques : `scenarios/cka|ckad|cks/` (examens) — `scenarios/ai/` (génération IA live).

---

## Killercoda : déployer son propre scénario

Voir `killercoda/README.md`. Le point d'entrée est `killercoda/bootstrap.sh`
(idempotent : kubectl + repo + install.sh + web auto-start). Le dossier
`killercoda/cka-ai-lab/` contient un exemple de scénario complet.

---

## Entraînement avec l'IA (opencode / Claude Code)

`AGENTS.md` définit le rôle **examinateur IA** :

1. **Jamais la solution complète d'un coup** — échelle d'indices 1→3
2. Vérifier **dans le cluster** (`kubectl get/describe`), pas sur parole
3. Rappeler les réflexes examen (contexte courant, `--dry-run=client -o yaml`)
4. **Examen adaptatif** : selon les résultats, l'IA saute des scénarios trop
   faciles, génère des variantes, des exercices de renforcement
5. **Génération live** → onglet web 🤖 (protocole complet dans `AGENTS.md`)

---

## Structure du projet

```
├── README.md                 ← vous êtes ici
├── AGENTS.md                 ← instructions agents IA (examinateur + génération live)
├── install.sh / run.sh       ← entry points (dispatch cka-sim/)
├── CKA/                      ← notes de cours (FR)
├── cka-sim/                  ← simulateur : scénarios, exams, UI web, terminal PTY
│   ├── cka_sim/              ← code python (web server, WS terminal, validator, db…)
│   ├── scenarios/cka|ckad|cks|ai/
│   ├── exams/<cert>/         ← web-exam.yaml / full-exam.yaml
│   └── data/cheatsheet.json
├── guides/                   ← anti-cheats examen (kubectl, jsonpath, jq, helm…)
├── killercoda/               ← bootstrap.sh + scénario Killercoda déployable
└── ressources/               ← repos GitHub gratuits + CKAD-exercises cloné
```

## Rappel examens ([cncf/curriculum](https://github.com/cncf/curriculum))

| Exam | Durée | Score | Notes |
|---|---|---|---|
| CKA | 2h | 66% | 2 tentatives + 2 sessions killer.sh |
| CKAD | 2h | 66% | orienté développement d'apps |
| CKS | 2h | 67% | **prérequis : CKA valide** |

## Dépannage

| Symptôme | Fix |
|---|---|
| Terminal web rouge « reconnecting » | le serveur web est down → `./run.sh web` (ou log `/tmp/cka-sim-web.log`) |
| Page web inaccessible (Killercoda) | Traffic Port ≠ 8080 ? Vérifier l'onglet **Traffic Port**, port **8080** |
| NodePort 30999 inaccessible (kind) | firewall / `kubectl port-forward svc/cka-exam 8080:80` |
| `kubectl top` vide | metrics-server pas prêt : `kubectl -n kube-system rollout status deploy/metrics-server` |
| Port 8080 déjà pris | `CKA_SIM_WEB_PORT=9090 ./run.sh web` + Traffic Port 9090 |
| Résultats effacés après reinstall | normaux si `db/reset` ; sinon la SQLite est dans `cka-sim/data/exam_state.db` |

Mise à jour des ressources clonées : `cd ressources/CKAD-exercises && git pull`
