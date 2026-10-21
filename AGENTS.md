# AGENTS.md — Instructions pour agents IA (opencode, Claude Code, Cursor…)

Ce dépôt est un **entraîneur aux certifications Kubernetes** (CKA / CKAD / CKS) :

```
CKA/            Notes de cours (FR)
cka-sim/        Simulateur d'examen local : vraies commandes kubectl sur cluster kind
guides/         Anti-cheats orientés examen (jsonpath, jq, helm, aliases…)
ressources/     Repos GitHub gratuits + CKAD-exercises cloné
killercoda/     Scénario Killercoda déployable + bootstrap.sh
```

## Commandes du simulateur

Entry points à la **racine du dépôt** (dispatchent vers `cka-sim/`) :

```bash
./run.sh list                 # banque CKA par défaut
./run.sh --cert ckad list     # banque CKAD (scénarios/ckad/)
./run.sh --cert cks list      # banque CKS (scénarios/cks/)
./run.sh run <id>             # lancer un scénario
./run.sh exam                 # examen complet chronométré (2h, noté)
./run.sh web                  # UI web d'examen (NodePort 30999)
./run.sh status               # état cluster/outils
bash install.sh               # setup complet (venv seulement si python externally-managed)
```

Navigation en session (`:back`, `:goto n`) : **ne réinitialise jamais** un scénario
(les changements sont conservés) ; `:reset` ré-applique explicitement le setup.

## Format d'un scénario (`cka-sim/scenarios/<cert>/<domaine>/<id>/scenario.yaml`)

```yaml
id: extract-image-deploy
title: "..."
domain: workloads        # 01-workloads…06-rbac
weight: 3
difficulty: medium
setup:
  apply: setup.yaml      # ressources pré-créées (optionnel)
question: |
  ...
hints:
  - { level: 1, text: "orientation : famille de commandes" }
  - { level: 2, text: "méthode de recherche : jq paths(scalars) / kubectl explain --recursive" }
  - { level: 3, text: "piège / astuce doc" }
check:
  assertions:
    - run: "kubectl get deploy web -o jsonpath='{...}'"
      contains: "nginx:1.21"
```

## Rôle « examinateur IA » — règles du jeu

Quand l'utilisateur s'entraîne (mode tutorat) :

1. **Ne JAMAIS donner la solution complète d'un coup** — suivre l'échelle d'indices :
   - Niveau 1 : orienter vers la famille de commandes (`kubectl get`, `explain`, `logs`…)
   - Niveau 2 : donner la *méthode de recherche* (`kubectl explain --recursive | grep`, `-o json | jq 'paths(scalars)'`, doc kubernetes.io)
   - Niveau 3 : donner la commande presque complète, laisser les détails
   - Solution complète uniquement sur demande explicite
2. **Vérifier dans le cluster**, pas sur parole : toujours confirmer avec `kubectl get/describe` réel.
3. Rappeler les réflexes examen : vérifier le contexte (`kubectl config current-context`), générer le YAML avec `--dry-run=client -o yaml`, ne jamais écrire de YAML à la main si évitable.
4. Corriger la *méthode* autant que le résultat (l'examen note l'état du cluster, pas le chemin).
5. En français par défaut (les notes de l'utilisateur sont en français).

## Générer de nouveaux scénarios

L'IA peut créer des scénarios en respectant le format ci-dessus, puis :
1. vérifier le YAML (`python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`),
2. tester les assertions à la main sur le cluster kind,
3. lancer `./run.sh run <id>` pour confirmer que setup + check passent.

## Déploiement Killercoda

Voir `killercoda/README.md`. Le point d'entrée est `killercoda/bootstrap.sh`
(idempotent : kubectl + kind + cluster + ce dépôt cloné dans `/root/cka-ckad-cks-prep`).

## Examen adaptatif piloté par IA (mode tutorat évolué)

L'IA a **accès total au cluster** (via kubectl) et au simulateur (`./run.sh`).
Elle peut générer un examen sur une thématique choisie, vérifier les résultats
en direct, et s'adapter.

### Protocole

1. **L'utilisateur choisit une thématique** (ex: "storage", "networking",
   "troubleshooting", "tout") et éventuellement un niveau.
2. **L'IA sélectionne les scénarios** :
   ```bash
   ./run.sh --cert cka list --domain storage    # voir les scénarios dispo
   ./run.sh --cert cka run <id>                  # lancer un scénario
   ```
3. **Pendant le scénario**, l'IA suit les règles d'indices (échelle §1-3),
   MAIS en plus elle peut :
   - vérifier l'état du cluster en direct (`kubectl get/describe` elle-même)
   - poser des questions de compréhension ("pourquoi ce paramètre ?")
   - faire des mini-démos (`kubectl explain` sur un champ précis)
4. **Après chaque scénario**, l'IA évalue le résultat :
   - SOLVED sans indice → passer au suivant, éventuellement monter en difficulté
   - SOLVED avec indices → noter le point faible, prévoir une variante
   - FAILED → diagnostiquer, donner un mini-cours ciblé, puis RETENTER
5. **Adaptation** : selon les résultats, l'IA peut :
   - **générer un nouveau scénario** à la volée (format YAML, `./run.sh run <id>`)
   - **modifier un scénario existant** (changer un paramètre, ajouter un piège)
   - **proposer un exercice de renforcement** sur le domaine faible
   - **sauter des scénarios** trop faciles pour accélérer

### Template de génération à la volée

```yaml
id: ai-<topic>-<n>
title: "Generated: <description>"
domain: <domain>
weight: 3
difficulty: <easy|medium|hard>
requires: {workers: 1}    # adapter au cluster détecté
setup:
  apply: setup.yaml        # ou script: pour les break/fix
question: |
  <énoncé concis, style examen>
hints:
  - { level: 1, text: "orientation" }
  - { level: 2, text: "méthode de recherche" }
  - { level: 3, text: "astuce/piège" }
check:
  assertions:
    - run: "kubectl ..."
      contains: "expected"
```

L'IA écrit ce YAML dans `scenarios/<cert>/<domain>/<id>/scenario.yaml` (+ setup.yaml),
puis lance `./run.sh run <id>` pour valider que setup + assertions passent.

## Onglet web « AI assisted Learning » (génération LIVE)

L'UI web (`./run.sh web`) expose un onglet **🤖 AI assisted Learning** avec :

1. **💬 AI teacher chat** — l'utilisateur discute avec l'IA directement depuis
   la page (« create a real hard scenario for cka »). Les messages sont dans
   SQLite (`ai_chat`) ; l'agent les lit/répond via l'API.
2. **Liste d'exercices générés live** — dropés dans `scenarios/ai/`, hot-reload.

### Protocole chat (l'agent opencode POLL et RÉPOND)

Pendant une session de tutorat, poller régulièrement (toutes les ~15 s) et
traiter les messages en attente :

```bash
# 1. lire les messages en attente (user messages non traités + thread) :
curl -s "localhost:8080/api/ai/chat" | jq '{pending, messages}'
#    (sur kind/NodePort : curl -s http://<node-ip>:30999/api/ai/chat)

# 2. faire ce que demande l'utilisateur (générer l'exercice — cf. ci-dessous),
#    puis répondre + marquer traité :
curl -s -X POST localhost:8080/api/ai/chat/reply \
     -H 'Content-Type: application/json' \
     -d '{"text":"Exercice ai-netpol-hard-1 créé (CKA networking, hard) — il apparaît dans la liste."}'
```

- Répondre **après** avoir réellement généré/testé l'exercice (ou expliquer
  pourquoi on refuse/ajuste).
- L'UI raffraîchit la liste d'exercices dès qu'une réponse arrive.

### Protocole de génération live

1. **L'utilisateur demande un exercice** (prompt libre, ex: « un exercice sur
   les NetworkPolicies avec un piège sur les namespaces »).
2. **L'IA écrit l'exercice** dans la banque dédiée :
   ```
   cka-sim/scenarios/ai/<id>/scenario.yaml   # même format que §Template
   cka-sim/scenarios/ai/<id>/setup.yaml      # optionnel (pré-création)
   ```
   - `id` unique et parlant : `ai-<topic>-<n>` (ex: `ai-netpol-1`)
   - `weight` = points de l'exercice, `difficulty` = easy|medium|hard
   - `setup.apply` prépare le cluster/namespace ; les assertions `check:`
     sont OBLIGATOIRES (c'est elles qui alimentent le bouton **Check**).
3. **Hot-reload** : le serveur web scanne `scenarios/ai/` à chaque appel de
   l'API (`/api/ai/list`, auto-refresh 15 s quand l'onglet est ouvert).
   Aucun restart, aucune interruption de l'examen en cours.
4. **Validation avant livraison** (l'IA teste son propre exercice) :
   ```bash
   kubectl apply -f cka-sim/scenarios/ai/<id>/setup.yaml   # le setup passe ?
   # résoudre l'exercice dans le cluster, puis :
   curl -X POST localhost:8080/api/ai/check -d '{"id":"<id>"}' -H 'Content-Type: application/json'
   # → tous "passed": true ; puis reset pour rendre l'exercice vierge :
   curl -X POST localhost:8080/api/ai/reset -d '{"id":"<id>"}' -H 'Content-Type: application/json'
   ```
   Vérifier aussi le YAML : `python3 -c "import yaml;yaml.safe_load(open('<file>'))"`.
5. **Scoring automatique** : hint 1 = -10 %, hint 2 = -25 %, hint 3 = -40 %,
   solution = 0 %. Status `pending → active → done` (validé) ou `skipped`.
   Une question validée **reste `done`** même si on la re-clique.
6. **Ne jamais modifier** les banques `scenarios/cka|ckad|cks/` pour la
   génération live — uniquement `scenarios/ai/` (séparation exam / AI).

### Contraintes

- Préparer le cluster **sans casser l'UI web** : n'utiliser que `kubectl
  apply/delete` ciblés (namespaces préfixés `ai-` si possible), jamais de
  reset global (`db/reset` / `:reset`) pendant qu'un examen tourne.
- Les placeholders `%CP%`, `%WORKER%`… sont substitués automatiquement dans
  question/hints — les utiliser pour les noms de nœuds.
- `requires: {workers: N}` : les exercices sont filtrés si le cluster est
  trop petit (détection auto).
