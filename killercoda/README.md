# Déploiement sur Killercoda

## Option A — usage immédiat (aucun compte Killercoda requis)

Sur n'importe quel playground **Ubuntu** de [killercoda.com](https://killercoda.com)
(catalogue → "Ubuntu" ou n'importe quel playground Linux avec Docker), colle :

```bash
curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/bootstrap.sh | bash
```

Puis :

```bash
cd /root/cka-ckad-cks-prep/cka-sim
./run.sh list && ./run.sh run create-deploy
```

Le script est **idempotent** : kubectl + kind + cluster 3 nœuds + dépôt cloné.

## Option B — scénario intégré à ton compte Killercoda

Le dossier `cka-ai-lab/` est un scénario Killercoda complet (`index.json`, steps,
`background.sh`). Pour le publier sur ton profil :

1. Crée un compte sur killercoda.com (login GitHub).
2. Crée une **org GitHub** dédiée (ex. `killercoda-<ton-pseudo>`) et invites ton compte.
3. Copie le contenu de ce dossier `killercoda/` dans un repo de cette org
   (chaque sous-dossier avec `index.json` devient un scénario) :
   ```bash
   cp -r killercoda/ /tmp/kc && cd /tmp/kc && rm README.md bootstrap.sh
   gh repo create killercoda-<pseudo>/cka-labs --public --source=. --push
   ```
4. Sur killercoda.com → ton profil listera le scénario *CKA Trainer Lab*.

## Utiliser l'IA comme examinateur (sur le playground)

```bash
curl -fsSL https://opencode.ai/install | bash
opencode auth login          # provider au choix (free tiers disponibles)
cd /root/cka-ckad-cks-prep && opencode
```

Le fichier `AGENTS.md` à la racine du dépôt donne à l'agent son rôle d'examinateur
(indices progressifs, vérification cluster, génération de scénarios).
