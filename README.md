# Préparation CKA / CKAD / CKS — Projet complet

Tout ce qu'il faut pour préparer les certifications Kubernetes **CNCF**, en un seul endroit.

> Repo : https://github.com/packbo/cka-ckad-cks-prep
> Déployable en 1 commande sur tout playground Ubuntu (Killercoda, Codespaces…) — voir `killercoda/README.md`.
> Prêt pour l'IA : `AGENTS.md` transforme opencode/Claude en examinateur (indices progressifs).

## Structure du projet

```
claude_course/
├── README.md                      ← vous êtes ici (index + plan d'entraînement)
├── AGENTS.md                      ← instructions pour agents IA (rôle examinateur)
├── CKA/                           ← notes de cours (exercices, scénarios, setup examen)
├── cka-sim/                       ← simulateur d'examen LOCAL (kind) avec indices progressifs
├── guides/                        ← anti-cheats orientés examen (kubectl, jsonpath, jq, helm…)
├── killercoda/                    ← scénario Killercoda + bootstrap.sh (déploiement 1 commande)
└── ressources/
    ├── repos-github-gratuits.md   ← tous les repos GitHub gratuits CKA/CKAD/CKS
    └── CKAD-exercises/            ← exercices CKAD clonés (dgkanatsios, 10k+ ★)
```

## Guides disponibles (`guides/`)

| Fichier | Contenu |
|---|---|
| `alias-raccourcis-examen.md` | Alias kubectl + setup 2 min début d'examen |
| `kubectl-workflow-examen.md` | Workflow kubectl orienté examen |
| `commandes-avancees.md` | Commandes avancées |
| `jsonpath-antiseche-express.md` | JSONPath express |
| `jsonpath-best-practices.md` | JSONPath bonnes pratiques |
| `kubectl-chaining-jsonpath.md` | Chaînage kubectl + JSONPath |
| `jq-scalars-paths-guide.md` | jq `paths(scalars)` — méthode de recherche |
| `grep-guide.md` | grep pour l'examen |
| `helm-guide-complet.md` | Helm complet (au programme du CKA depuis v1.31+) |

## Plan d'entraînement recommandé

1. **Théorie** → lire `CKA/` + les liens de `ressources/repos-github-gratuits.md`
2. **Drill quotidien (30-60 min)** → [Killercoda](https://killercoda.com) (gratuit, 1h/session)
   - Playground CKA : https://killercoda.com/killer-shell-cka
   - Playground CKS : https://killercoda.com/killer-shell-cks
3. **Exercices CKAD** → `ressources/CKAD-exercises/` (par domaine : core concepts, pod design, config…)
4. **Simulation d'examen** → `./cka-sim/run.sh exam` (2h, noté, avec indices)
5. **Dress rehearsal** → les 2 sessions killer.sh incluses avec l'achat de l'examen (à J-7)

## Rappel examens (vérifier sur [cncf/curriculum](https://github.com/cncf/curriculum))

| Exam | Durée | Score | Notes |
|---|---|---|---|
| CKA | 2h | 66% | 2 tentatives + 2 sessions killer.sh |
| CKAD | 2h | 66% | orienté développement d'apps |
| CKS | 2h | 67% | **prérequis : CKA valide** |

## Mise à jour des ressources clonées

```bash
cd ressources/CKAD-exercises && git pull
```
