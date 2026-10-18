#!/usr/bin/env bash
# Déploie ingress-nginx + une page web (podinfo) exposée sur le port 80 de la VM.
# Sur Killercoda : l'URL publique s'affiche dans l'onglet « Traffic » du scénario.
# Prérequis : cluster créé avec CKA_SIM_INGRESS=1 (cas par défaut du bootstrap Killercoda).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log() { echo "[ingress-demo] $*"; }

if ! command -v kubectl >/dev/null 2>&1 || [ "$(kubectl get nodes --no-headers 2>/dev/null | wc -l)" -lt 1 ]; then
  echo "[ingress-demo] ERREUR : aucun cluster. Lance d'abord killercoda/bootstrap.sh"; exit 1
fi

# Pré-vérif : le nœud control-plane doit porter le label ingress-ready (= cluster créé avec CKA_SIM_INGRESS=1)
if ! kubectl get nodes -o json | jq -e '.items[].metadata.labels["ingress-ready"] == "true"' >/dev/null 2>&1; then
  cat <<'EOF'
[ingress-demo] Ce cluster n'a PAS été créé avec les ports 80/443 mappés (CKA_SIM_INGRESS=1).
Pour l'activer (⚠ recrée le cluster = remise à zéro) :
  kind delete cluster --name cka-sim
  CKA_SIM_INGRESS=1 bash cka-sim/install.sh
  bash killercoda/ingress-demo.sh
EOF
  exit 1
fi

log "installation ingress-nginx (image pull ~1 min)..."
ING_URL="https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.1/deploy/static/provider/kind/deploy.yaml"
curl -sfI "$ING_URL" >/dev/null || ING_URL="https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
kubectl apply -f "$ING_URL"

log "attente du controller ingress-nginx..."
kubectl wait --namespace ingress-nginx --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=300s

log "déploiement de la page web (podinfo) + Ingress..."
kubectl apply -f "$SCRIPT_DIR/ingress-demo-app.yaml"
kubectl wait --for=condition=available deployment/podinfo --timeout=180s

log "test local :"
curl -s http://localhost/ | grep -o "<title>.*</title>" || curl -s http://localhost/ | head -3

cat <<'EOF'

✅ Page web en ligne sur le port 80 de la VM.
   → Killercoda : ouvre l'onglet « Traffic » (à côté du Terminal) pour l'URL publique.
   → Local      : http://localhost
EOF
