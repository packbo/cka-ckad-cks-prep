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
