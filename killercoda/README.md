# Déploiement sur Killercoda

## Option A — usage immédiat (aucun compte Killercoda requis)

Sur n'importe quel playground **Ubuntu** de [killercoda.com](https://killercoda.com)
(catalogue → "Ubuntu" ou n'importe quel playground Linux avec Docker), colle :

```bash
curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/bootstrap.sh | bash
```

À la fin, **l'UI web démarre automatiquement en arrière-plan** et le terminal
affiche le port à ouvrir. Sur un playground avec cluster **préinstallé**
(ex: *Kubernetes Cluster* de Killercoda) :

```
───────────────────────────────────────────────────────────────
 🎓  WEB EXAM UI READY — running in the background on :8080
 ➜  Open the "Traffic Port" tab (top bar, right of "Terminal")
    and enter the port:   8080
───────────────────────────────────────────────────────────────
```

Sur un playground Ubuntu **vierge** (pas de cluster), le bootstrap installe
docker + kind et l'UI est servie en **NodePort 30999** (URL affichée).

En ligne de commande aussi :

```bash
cd /root/cka-ckad-cks-prep/cka-sim
./run.sh list && ./run.sh run create-deploy
```

Le script est **idempotent** : kubectl + gh + cluster + dépôt cloné + web auto-start.

### Tout-en-un (cluster + IA : npm → opencode → init)

Sur un playground Ubuntu vierge, la commande unique qui installe Node/npm, opencode,
puis initialise repo + cluster :

```bash
curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/ai-setup.sh | bash
```

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

## Page web publique via Ingress (ports 80/443)

Killercoda ne donne pas d'IP publique directe : il **route le trafic HTTP (80/443)**
vers la VM via une URL proxy, visible dans l'onglet **« Traffic »** du scénario.

Le bootstrap crée le cluster avec `CKA_SIM_INGRESS=1` → ports 80/443 mappés sur le
control-plane. Pour publier une page web de démo (ingress-nginx + podinfo) :

```bash
curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/ingress-demo.sh | bash
```

En local (⚠ recrée le cluster) :

```bash
cd cka-sim && ./run.sh down
CKA_SIM_INGRESS=1 bash install.sh && bash ../killercoda/ingress-demo.sh
```

## Utiliser l'IA comme examinateur (sur le playground)

```bash
curl -fsSL https://opencode.ai/install | bash
opencode auth login          # provider au choix (free tiers disponibles)
cd /root/cka-ckad-cks-prep && opencode
```

Le fichier `AGENTS.md` à la racine du dépôt donne à l'agent son rôle d'examinateur
(indices progressifs, vérification cluster, génération de scénarios).
