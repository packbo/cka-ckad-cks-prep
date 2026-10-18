# Guide Helm Complet - Installation, Recherche et Gestion

## Table des matières
1. [Installation de Helm](#installation-de-helm)
2. [Trouver des Charts et Repositories](#trouver-des-charts-et-repositories)
3. [Installer des Charts](#installer-des-charts)
4. [Gérer les Values](#gérer-les-values)
5. [Update et Upgrade](#update-et-upgrade)
6. [Debugging et Troubleshooting](#debugging-et-troubleshooting)
7. [Commandes Avancées](#commandes-avancées)

---

## Installation de Helm

### Installer Helm
```bash
# Méthode 1 : Script officiel (recommandé)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Méthode 2 : Via package manager
# Ubuntu/Debian
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
sudo apt-get install apt-transport-https --yes
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm

# Snap
sudo snap install helm --classic

# macOS
brew install helm

# Vérifier l'installation
helm version
helm version --short
```

### Configuration initiale
```bash
# Ajouter l'auto-complétion
# Bash
echo 'source <(helm completion bash)' >> ~/.bashrc
source ~/.bashrc

# Zsh
echo 'source <(helm completion zsh)' >> ~/.zshrc
source ~/.zshrc

# Vérifier la configuration
helm env
```

---

## Trouver des Charts et Repositories

### 1. Artifact Hub (Hub officiel)

#### Via le site web
```bash
# Ouvrir dans le navigateur
https://artifacthub.io

# Chercher un chart, par exemple :
# - nginx
# - postgresql
# - prometheus
# - cert-manager
```

#### Via la ligne de commande
```bash
# Helm 3 ne vient plus avec des repos pré-configurés
# Il faut les ajouter manuellement

# Chercher sur Artifact Hub via l'API
curl -s "https://artifacthub.io/api/v1/packages/search?kind=0&ts_query=nginx" | jq -r '.packages[] | "\(.name) - \(.repository.name) - \(.repository.url)"'

# Ou utiliser le navigateur web pour chercher et copier les commandes helm repo add
```

### 2. Ajouter des repositories populaires

```bash
# Bitnami (très populaire, bien maintenu)
helm repo add bitnami https://charts.bitnami.com/bitnami

# Helm stable (déprécié mais encore utilisé)
helm repo add stable https://charts.helm.sh/stable

# Prometheus community
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Grafana
helm repo add grafana https://grafana.github.io/helm-charts

# Ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

# Cert-manager
helm repo add jetstack https://charts.jetstack.io

# Elastic
helm repo add elastic https://helm.elastic.co

# GitLab
helm repo add gitlab https://charts.gitlab.io

# Harbor
helm repo add harbor https://helm.goharbor.io

# Kong
helm repo add kong https://charts.konghq.com

# Argo
helm repo add argo https://argoproj.github.io/argo-helm

# Metrics Server
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/

# Longhorn (storage)
helm repo add longhorn https://charts.longhorn.io

# Rancher
helm repo add rancher-latest https://releases.rancher.com/server-charts/latest

# Mettre à jour tous les repos
helm repo update
```

### 3. Lister les repositories configurés

```bash
# Voir tous les repos ajoutés
helm repo list

# Sortie :
# NAME                    URL
# bitnami                 https://charts.bitnami.com/bitnami
# prometheus-community    https://prometheus-community.github.io/helm-charts
```

### 4. Chercher des charts

#### Chercher dans tous les repos configurés
```bash
# Chercher "nginx" dans tous les repos
helm search repo nginx

# Résultat :
# NAME                            CHART VERSION   APP VERSION     DESCRIPTION
# bitnami/nginx                   15.14.0         1.25.4          NGINX is a web server
# bitnami/nginx-ingress-controller 10.0.0         1.9.5           NGINX Ingress Controller

# Chercher avec version
helm search repo nginx --versions

# Chercher avec regex
helm search repo '^nginx$'

# Chercher tout (attention, beaucoup de résultats)
helm search repo .
```

#### Chercher sur Artifact Hub (depuis Helm)
```bash
# Chercher sur le hub (nécessite connexion internet)
helm search hub nginx

# Avec plus de détails
helm search hub nginx --max-col-width=0

# Résultat inclut l'URL du chart sur Artifact Hub
```

### 5. Obtenir des informations sur un chart

```bash
# Voir les infos du chart (depuis le repo)
helm show chart bitnami/nginx

# Voir le README
helm show readme bitnami/nginx

# Voir les values par défaut (TRÈS IMPORTANT)
helm show values bitnami/nginx

# Voir tout
helm show all bitnami/nginx

# Sauvegarder les values dans un fichier
helm show values bitnami/nginx > nginx-default-values.yaml
```

### 6. Inspecter un chart sans l'installer

```bash
# Télécharger le chart sans l'installer
helm pull bitnami/nginx

# Résultat : nginx-15.14.0.tgz

# Décompresser
helm pull bitnami/nginx --untar

# Résultat : dossier nginx/ avec tous les fichiers

# Télécharger une version spécifique
helm pull bitnami/nginx --version 15.14.0

# Voir la structure du chart
helm pull bitnami/nginx --untar && tree nginx/

# Structure typique :
# nginx/
# ├── Chart.yaml          # Métadonnées du chart
# ├── values.yaml         # Values par défaut
# ├── templates/          # Templates Kubernetes
# │   ├── deployment.yaml
# │   ├── service.yaml
# │   ├── ingress.yaml
# │   └── ...
# ├── charts/             # Dépendances
# └── README.md
```

---

## Installer des Charts

### 1. Installation basique

```bash
# Syntaxe de base
helm install [RELEASE_NAME] [CHART] [flags]

# Exemple : installer nginx
helm install my-nginx bitnami/nginx

# Avec namespace spécifique
helm install my-nginx bitnami/nginx -n production

# Créer le namespace s'il n'existe pas
helm install my-nginx bitnami/nginx -n production --create-namespace

# Version spécifique
helm install my-nginx bitnami/nginx --version 15.14.0
```

### 2. Installation avec values personnalisées

#### Méthode 1 : Fichier de values
```bash
# 1. Récupérer les values par défaut
helm show values bitnami/nginx > my-values.yaml

# 2. Éditer my-values.yaml
# Modifier seulement ce qui vous intéresse

# 3. Installer avec les values personnalisées
helm install my-nginx bitnami/nginx -f my-values.yaml

# Avec plusieurs fichiers (le dernier écrase les précédents)
helm install my-nginx bitnami/nginx -f values.yaml -f values-prod.yaml
```

#### Méthode 2 : Paramètres en ligne de commande
```bash
# Avec --set
helm install my-nginx bitnami/nginx \
  --set service.type=LoadBalancer \
  --set replicaCount=3

# Valeurs imbriquées avec points
helm install my-nginx bitnami/nginx \
  --set service.type=LoadBalancer \
  --set ingress.enabled=true \
  --set ingress.hostname=example.com

# Tableaux
helm install my-nginx bitnami/nginx \
  --set ingress.hosts[0].name=example.com \
  --set ingress.hosts[0].path=/

# Combiner fichier et --set (--set a priorité)
helm install my-nginx bitnami/nginx \
  -f my-values.yaml \
  --set replicaCount=5
```

#### Méthode 3 : Values depuis stdin
```bash
# Depuis un fichier généré dynamiquement
cat <<EOF | helm install my-nginx bitnami/nginx -f -
replicaCount: 3
service:
  type: LoadBalancer
ingress:
  enabled: true
EOF
```

### 3. Dry-run et Validation

```bash
# Dry-run (ne pas installer, juste voir ce qui serait créé)
helm install my-nginx bitnami/nginx --dry-run

# Dry-run avec debug (voir les manifests générés)
helm install my-nginx bitnami/nginx --dry-run --debug

# Sauvegarder les manifests dans un fichier
helm install my-nginx bitnami/nginx --dry-run --debug > manifests.yaml

# Valider le chart avant installation
helm lint ./my-chart

# Template (générer les manifests sans installer)
helm template my-nginx bitnami/nginx > manifests.yaml

# Template avec values
helm template my-nginx bitnami/nginx -f my-values.yaml > manifests.yaml
```

### 4. Options d'installation avancées

```bash
# Attendre que toutes les ressources soient ready
helm install my-nginx bitnami/nginx --wait

# Avec timeout
helm install my-nginx bitnami/nginx --wait --timeout 10m

# Générer un nom automatique
helm install bitnami/nginx --generate-name

# Avec annotations
helm install my-nginx bitnami/nginx \
  --set commonAnnotations.team=platform \
  --set commonAnnotations.environment=production

# Désactiver les hooks
helm install my-nginx bitnami/nginx --no-hooks

# Mode atomic (rollback si échec)
helm install my-nginx bitnami/nginx --atomic

# Remplacer si existe déjà
helm install my-nginx bitnami/nginx --replace
```

---

## Gérer les Values

### 1. Voir les values par défaut d'un chart

```bash
# Values par défaut du chart
helm show values bitnami/nginx

# Sauvegarder dans un fichier
helm show values bitnami/nginx > nginx-defaults.yaml

# Voir seulement certaines sections (avec grep)
helm show values bitnami/nginx | grep -A 20 "ingress:"

# Avec yq pour plus de contrôle
helm show values bitnami/nginx | yq e '.ingress' -

# Compter les options disponibles
helm show values bitnami/nginx | grep -c "^[a-z]"
```

### 2. Voir les values d'une release installée

```bash
# Values utilisées pour l'installation
helm get values my-nginx

# Toutes les values (y compris les valeurs par défaut)
helm get values my-nginx --all

# En YAML
helm get values my-nginx -o yaml

# En JSON
helm get values my-nginx -o json

# Sauvegarder
helm get values my-nginx --all > current-values.yaml

# Revision spécifique
helm get values my-nginx --revision 1
```

### 3. Comparer les values

```bash
# Comparer values par défaut vs installées
diff <(helm show values bitnami/nginx) <(helm get values my-nginx --all)

# Avec colordiff (plus lisible)
colordiff -u <(helm show values bitnami/nginx) <(helm get values my-nginx --all)

# Voir seulement vos modifications
helm get values my-nginx
```

### 4. Explorer les values avec jq/yq

```bash
# Extraire des sections spécifiques
helm show values bitnami/nginx | yq e '.service' -
helm show values bitnami/nginx | yq e '.ingress' -
helm show values bitnami/nginx | yq e '.resources' -

# Lister toutes les clés de premier niveau
helm show values bitnami/nginx | yq e 'keys' -

# Trouver toutes les valeurs "enabled"
helm show values bitnami/nginx | yq e '.. | select(has("enabled")) | .enabled' -

# Chercher une valeur spécifique
helm show values bitnami/nginx | yq e '.service.type' -
```

### 5. Values importantes à connaître (communs à la plupart des charts)

#### Structure typique de values.yaml
```yaml
# Nombre de replicas
replicaCount: 1

# Image
image:
  registry: docker.io
  repository: bitnami/nginx
  tag: 1.25.4
  pullPolicy: IfNotPresent
  pullSecrets: []

# Service
service:
  type: ClusterIP        # ClusterIP, NodePort, LoadBalancer
  port: 80
  targetPort: http
  annotations: {}

# Ingress
ingress:
  enabled: false
  className: nginx
  hostname: example.com
  path: /
  pathType: Prefix
  tls: false
  annotations: {}

# Resources
resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Autoscaling
autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPU: 80
  targetMemory: 80

# Persistence
persistence:
  enabled: false
  storageClass: ""
  accessMode: ReadWriteOnce
  size: 8Gi

# SecurityContext
podSecurityContext:
  fsGroup: 1001
containerSecurityContext:
  runAsUser: 1001
  runAsNonRoot: true

# Node affinity
nodeSelector: {}
tolerations: []
affinity: {}

# Probes
livenessProbe:
  enabled: true
  path: /
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  enabled: true
  path: /
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 6. Créer un fichier values personnalisé

```bash
# Méthode 1 : Partir des defaults
helm show values bitnami/nginx > my-values.yaml
# Éditer et garder seulement ce que vous modifiez

# Méthode 2 : Créer from scratch
cat > my-values.yaml <<EOF
replicaCount: 3

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  hostname: myapp.example.com
  tls: true

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
EOF

# Valider votre fichier
yq e '.' my-values.yaml

# Tester avec dry-run
helm install my-nginx bitnami/nginx -f my-values.yaml --dry-run --debug
```

### 7. Bonnes pratiques pour les values

```bash
# Organiser par environnement
values-dev.yaml
values-staging.yaml
values-prod.yaml

# Utiliser avec
helm install my-nginx bitnami/nginx -f values-common.yaml -f values-prod.yaml

# Secrets et données sensibles
# ❌ Ne JAMAIS mettre dans values.yaml :
password: super-secret-password

# ✅ Utiliser --set ou des secrets externes
helm install my-db bitnami/postgresql \
  --set auth.password=$(kubectl get secret db-password -o jsonpath='{.data.password}' | base64 -d)

# Ou utiliser helm-secrets plugin
helm secrets install my-db bitnami/postgresql -f secrets.yaml
```

---

## Update et Upgrade

### 1. Lister les releases installées

```bash
# Toutes les releases
helm list

# Dans un namespace spécifique
helm list -n production

# Dans tous les namespaces
helm list -A

# Avec plus de détails
helm list -o yaml
helm list -o json

# Filtrer par status
helm list --deployed
helm list --failed
helm list --pending

# Filtrer par nom
helm list --filter '^my-'
helm list --filter 'nginx'
```

### 2. Voir l'historique d'une release

```bash
# Historique
helm history my-nginx

# Résultat :
# REVISION  UPDATED                   STATUS      CHART         APP VERSION   DESCRIPTION
# 1         Mon Jan 15 10:00:00 2024  deployed    nginx-15.14.0 1.25.4        Install complete

# Dans un namespace
helm history my-nginx -n production

# Format JSON
helm history my-nginx -o json
```

### 3. Mettre à jour le repository

```bash
# Mettre à jour tous les repos
helm repo update

# Mettre à jour un repo spécifique
helm repo update bitnami

# Voir les mises à jour disponibles pour vos releases
# (pas de commande native, script custom)
for release in $(helm list -q); do
    chart=$(helm list -o json | jq -r ".[] | select(.name==\"$release\") | .chart")
    echo "Release: $release - Current chart: $chart"
done
```

### 4. Upgrade d'une release

```bash
# Upgrade basique
helm upgrade my-nginx bitnami/nginx

# Upgrade vers une version spécifique
helm upgrade my-nginx bitnami/nginx --version 15.15.0

# Upgrade avec nouveaux values
helm upgrade my-nginx bitnami/nginx -f my-values.yaml

# Upgrade avec --set
helm upgrade my-nginx bitnami/nginx --set replicaCount=5

# Réutiliser les values de l'installation précédente
helm upgrade my-nginx bitnami/nginx --reuse-values

# Réinitialiser aux values par défaut + vos nouveaux values
helm upgrade my-nginx bitnami/nginx --reset-values -f my-values.yaml

# Install ou upgrade (installe si n'existe pas)
helm upgrade --install my-nginx bitnami/nginx -f my-values.yaml

# Avec wait et timeout
helm upgrade my-nginx bitnami/nginx --wait --timeout 10m

# Atomic (rollback si échec)
helm upgrade my-nginx bitnami/nginx --atomic

# Dry-run pour voir ce qui changerait
helm upgrade my-nginx bitnami/nginx --dry-run --debug

# Forcer le re-déploiement même si rien ne change
helm upgrade my-nginx bitnami/nginx --force
```

### 5. Diff avant upgrade (plugin)

```bash
# Installer le plugin helm-diff
helm plugin install https://github.com/databus23/helm-diff

# Voir les différences avant upgrade
helm diff upgrade my-nginx bitnami/nginx -f my-values.yaml

# Avec trois-way diff
helm diff upgrade my-nginx bitnami/nginx -f my-values.yaml --three-way-merge

# Sauvegarder le diff
helm diff upgrade my-nginx bitnami/nginx -f my-values.yaml > upgrade-diff.txt
```

### 6. Rollback

```bash
# Voir l'historique
helm history my-nginx

# Rollback à la version précédente
helm rollback my-nginx

# Rollback à une révision spécifique
helm rollback my-nginx 1

# Avec wait
helm rollback my-nginx --wait

# Dry-run
helm rollback my-nginx --dry-run

# Avec cleanup on fail
helm rollback my-nginx --cleanup-on-fail
```

### 7. Stratégies d'upgrade

#### Blue-Green deployment
```bash
# 1. Installer la nouvelle version avec un nom différent
helm install my-nginx-v2 bitnami/nginx -f values-v2.yaml

# 2. Tester
kubectl get svc my-nginx-v2

# 3. Basculer le trafic (via ingress ou service)
kubectl patch service main-service -p '{"spec":{"selector":{"app":"my-nginx-v2"}}}'

# 4. Supprimer l'ancienne version
helm uninstall my-nginx
```

#### Canary deployment (avec Flagger)
```bash
# Utiliser Flagger pour canary progressif
helm upgrade my-nginx bitnami/nginx --set canary.enabled=true
```

---

## Debugging et Troubleshooting

### 1. Vérifier le status d'une release

```bash
# Status détaillé
helm status my-nginx

# Dans un namespace
helm status my-nginx -n production

# Voir les notes d'installation
helm get notes my-nginx

# Voir tous les manifests déployés
helm get manifest my-nginx

# Sauvegarder les manifests
helm get manifest my-nginx > deployed-manifests.yaml

# Voir les hooks
helm get hooks my-nginx
```

### 2. Debugging lors de l'installation

```bash
# Mode debug
helm install my-nginx bitnami/nginx --debug

# Dry-run + debug
helm install my-nginx bitnami/nginx --dry-run --debug

# Template avec debug
helm template my-nginx bitnami/nginx --debug

# Voir les valeurs computées
helm install my-nginx bitnami/nginx --dry-run --debug 2>&1 | grep -A 1000 "COMPUTED VALUES:"
```

### 3. Problèmes courants

#### Chart introuvable
```bash
# ❌ Error: chart "nginx" not found
# ✅ Solution : Mettre à jour les repos
helm repo update

# ✅ Ou ajouter le repo
helm repo add bitnami https://charts.bitnami.com/bitnami
```

#### Release déjà existante
```bash
# ❌ Error: release "my-nginx" already exists
# ✅ Solution 1 : Upgrade au lieu d'install
helm upgrade my-nginx bitnami/nginx

# ✅ Solution 2 : Upgrade --install
helm upgrade --install my-nginx bitnami/nginx

# ✅ Solution 3 : Uninstall puis install
helm uninstall my-nginx
helm install my-nginx bitnami/nginx
```

#### Timeout
```bash
# ❌ Error: timed out waiting for the condition
# ✅ Solution : Augmenter le timeout
helm install my-nginx bitnami/nginx --timeout 15m

# Ou vérifier les pods
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

#### Values incorrect
```bash
# ❌ Error: validation failed
# ✅ Solution : Valider votre YAML
yq e '.' my-values.yaml

# Voir ce qui est appliqué
helm install my-nginx bitnami/nginx -f my-values.yaml --dry-run --debug
```

### 4. Nettoyer les releases

```bash
# Uninstall
helm uninstall my-nginx

# Uninstall avec namespace
helm uninstall my-nginx -n production

# Garder l'historique (pour rollback potentiel)
helm uninstall my-nginx --keep-history

# Purger complètement (supprimer l'historique)
helm uninstall my-nginx

# Lister les releases uninstalled (si --keep-history utilisé)
helm list --uninstalled
helm list --all

# Voir les releases dans tous les états
helm list -A --all
```

---

## Commandes Avancées

### 1. Gestion des repositories

```bash
# Ajouter un repo
helm repo add bitnami https://charts.bitnami.com/bitnami

# Lister les repos
helm repo list

# Mettre à jour les repos
helm repo update

# Supprimer un repo
helm repo remove bitnami

# Voir l'index d'un repo
helm repo index .

# Chercher dans un repo spécifique
helm search repo bitnami/nginx
```

### 2. Créer son propre chart

```bash
# Créer un nouveau chart
helm create my-app

# Structure créée :
# my-app/
# ├── Chart.yaml
# ├── values.yaml
# ├── templates/
# │   ├── deployment.yaml
# │   ├── service.yaml
# │   ├── ingress.yaml
# │   └── _helpers.tpl
# └── charts/

# Packager le chart
helm package my-app

# Résultat : my-app-0.1.0.tgz

# Installer depuis un chart local
helm install my-release ./my-app

# Ou depuis le package
helm install my-release ./my-app-0.1.0.tgz

# Linter le chart
helm lint ./my-app

# Tester le template
helm template my-release ./my-app
```

### 3. Dépendances de charts

```bash
# Chart.yaml avec dépendances
cat > Chart.yaml <<EOF
apiVersion: v2
name: my-app
version: 0.1.0
dependencies:
  - name: postgresql
    version: 12.x.x
    repository: https://charts.bitnami.com/bitnami
  - name: redis
    version: 17.x.x
    repository: https://charts.bitnami.com/bitnami
EOF

# Télécharger les dépendances
helm dependency update ./my-app

# Lister les dépendances
helm dependency list ./my-app

# Build les dépendances
helm dependency build ./my-app
```

### 4. Plugins Helm utiles

```bash
# Lister les plugins installés
helm plugin list

# helm-diff (voir les différences)
helm plugin install https://github.com/databus23/helm-diff
helm diff upgrade my-nginx bitnami/nginx -f my-values.yaml

# helm-secrets (gérer les secrets chiffrés)
helm plugin install https://github.com/jkroepke/helm-secrets
helm secrets install my-app ./my-chart -f secrets.yaml

# helm-dashboard (UI web pour Helm)
helm plugin install https://github.com/komodorio/helm-dashboard
helm dashboard

# helm-docs (générer documentation)
helm plugin install https://github.com/norwoodj/helm-docs
helm docs

# Mettre à jour un plugin
helm plugin update helm-diff

# Supprimer un plugin
helm plugin uninstall helm-diff
```

### 5. Variables d'environnement Helm

```bash
# Voir la config Helm
helm env

# Variables importantes
HELM_CACHE_HOME      # Cache des repos
HELM_CONFIG_HOME     # Configuration
HELM_DATA_HOME       # Data (repos, plugins)
KUBECONFIG          # Config Kubernetes

# Changer le namespace par défaut
export HELM_NAMESPACE=production
helm list  # Liste dans production

# Debug mode global
export HELM_DEBUG=1
helm install my-nginx bitnami/nginx
```

### 6. Travailler avec des charts OCI (registries)

```bash
# Login à un registry OCI
helm registry login registry.example.com

# Push un chart vers OCI registry
helm push my-chart-0.1.0.tgz oci://registry.example.com/charts

# Install depuis OCI registry
helm install my-release oci://registry.example.com/charts/my-chart --version 0.1.0

# Logout
helm registry logout registry.example.com
```

### 7. Hooks Helm

```bash
# Les hooks permettent d'exécuter des actions à certains moments
# Types de hooks :
# - pre-install    : Avant l'installation
# - post-install   : Après l'installation
# - pre-delete     : Avant la suppression
# - post-delete    : Après la suppression
# - pre-upgrade    : Avant l'upgrade
# - post-upgrade   : Après l'upgrade
# - pre-rollback   : Avant le rollback
# - post-rollback  : Après le rollback
# - test           : Quand `helm test` est exécuté

# Exemple de hook dans un template
cat > templates/pre-install-job.yaml <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-pre-install
  annotations:
    "helm.sh/hook": pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation
spec:
  template:
    spec:
      containers:
      - name: pre-install
        image: busybox
        command: ['sh', '-c', 'echo Pre-install hook']
      restartPolicy: Never
EOF
```

### 8. Tests Helm

```bash
# Créer un test dans templates/tests/
cat > templates/tests/test-connection.yaml <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: "{{ .Release.Name }}-test-connection"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
  - name: wget
    image: busybox
    command: ['wget']
    args: ['{{ .Release.Name }}:{{ .Values.service.port }}']
  restartPolicy: Never
EOF

# Exécuter les tests
helm test my-nginx

# Voir les logs des tests
helm test my-nginx --logs
```

---

## Workflows et Best Practices

### Workflow 1 : Installer une application depuis zéro

```bash
# 1. Trouver le chart
helm search hub postgresql

# 2. Ajouter le repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 3. Voir les values
helm show values bitnami/postgresql > postgresql-values.yaml

# 4. Éditer les values
cat > my-postgresql-values.yaml <<EOF
auth:
  postgresPassword: my-secure-password
  database: myapp
primary:
  persistence:
    enabled: true
    size: 10Gi
resources:
  requests:
    memory: 256Mi
    cpu: 250m
  limits:
    memory: 512Mi
    cpu: 500m
EOF

# 5. Tester avec dry-run
helm install my-db bitnami/postgresql -f my-postgresql-values.yaml --dry-run --debug

# 6. Installer
helm install my-db bitnami/postgresql -f my-postgresql-values.yaml --wait

# 7. Vérifier
helm status my-db
kubectl get pods
```

### Workflow 2 : Upgrade en production (safe)

```bash
# 1. Backup des values actuelles
helm get values my-app --all > backup-values-$(date +%Y%m%d).yaml

# 2. Voir l'historique
helm history my-app

# 3. Mettre à jour le repo
helm repo update

# 4. Voir les différences (avec plugin diff)
helm diff upgrade my-app bitnami/nginx -f new-values.yaml

# 5. Dry-run
helm upgrade my-app bitnami/nginx -f new-values.yaml --dry-run --debug

# 6. Upgrade avec atomic (rollback auto si échec)
helm upgrade my-app bitnami/nginx -f new-values.yaml --atomic --wait --timeout 10m

# 7. Vérifier
helm status my-app
kubectl get pods

# 8. Si problème, rollback
helm rollback my-app
```

### Workflow 3 : Gérer plusieurs environnements

```bash
# Structure des fichiers
my-app/
├── Chart.yaml
├── values.yaml              # Values par défaut
├── values-dev.yaml          # Override pour dev
├── values-staging.yaml      # Override pour staging
├── values-prod.yaml         # Override pour prod
└── templates/

# Install dev
helm install my-app ./my-app -f ./my-app/values-dev.yaml -n dev --create-namespace

# Install staging
helm install my-app ./my-app -f ./my-app/values-staging.yaml -n staging --create-namespace

# Install prod
helm install my-app ./my-app -f ./my-app/values-prod.yaml -n prod --create-namespace

# Upgrade tous les environnements
for env in dev staging prod; do
    helm upgrade my-app ./my-app -f ./my-app/values-${env}.yaml -n ${env}
done
```

### Workflow 4 : Debugging d'une installation qui échoue

```bash
# 1. Voir le status
helm status my-app

# 2. Voir les manifests déployés
helm get manifest my-app

# 3. Voir les values utilisées
helm get values my-app --all

# 4. Vérifier les pods
kubectl get pods -l app.kubernetes.io/instance=my-app

# 5. Décrire les pods problématiques
kubectl describe pod <pod-name>

# 6. Voir les logs
kubectl logs <pod-name>

# 7. Voir les events
kubectl get events --sort-by='.lastTimestamp'

# 8. Re-tester avec debug
helm upgrade my-app bitnami/nginx --debug --dry-run

# 9. Si nécessaire, uninstall et réinstall
helm uninstall my-app
helm install my-app bitnami/nginx -f my-values.yaml --debug --wait
```

---

## Cheat Sheet Helm

```bash
# ===== REPOS =====
helm repo add <name> <url>              # Ajouter un repo
helm repo list                          # Lister les repos
helm repo update                        # Mettre à jour les repos
helm repo remove <name>                 # Supprimer un repo

# ===== SEARCH =====
helm search repo <keyword>              # Chercher dans les repos
helm search hub <keyword>               # Chercher sur Artifact Hub
helm show values <chart>                # Voir les values par défaut
helm show chart <chart>                 # Voir les infos du chart
helm show readme <chart>                # Voir le README

# ===== INSTALL =====
helm install <name> <chart>                      # Installer
helm install <name> <chart> -f values.yaml       # Avec fichier values
helm install <name> <chart> --set key=value      # Avec --set
helm install <name> <chart> --dry-run --debug    # Dry-run
helm install <name> <chart> --wait               # Attendre que ready
helm upgrade --install <name> <chart>            # Install ou upgrade

# ===== LIST & STATUS =====
helm list                               # Lister les releases
helm list -A                            # Dans tous les namespaces
helm list --all                         # Tous les états
helm status <name>                      # Status d'une release
helm history <name>                     # Historique

# ===== GET =====
helm get values <name>                  # Voir les values utilisées
helm get values <name> --all            # Avec les defaults
helm get manifest <name>                # Voir les manifests
helm get notes <name>                   # Voir les notes

# ===== UPGRADE =====
helm upgrade <name> <chart>                      # Upgrade
helm upgrade <name> <chart> -f values.yaml       # Avec values
helm upgrade <name> <chart> --reuse-values       # Réutiliser values
helm upgrade <name> <chart> --atomic             # Rollback si échec

# ===== ROLLBACK =====
helm rollback <name>                    # Rollback à la version précédente
helm rollback <name> <revision>         # Rollback à une révision

# ===== UNINSTALL =====
helm uninstall <name>                   # Désinstaller
helm uninstall <name> --keep-history    # Garder l'historique

# ===== TEMPLATE & DEBUG =====
helm template <name> <chart>            # Générer les manifests
helm lint <chart>                       # Valider un chart
helm get manifest <name>                # Voir les manifests déployés

# ===== PACKAGES =====
helm pull <chart>                       # Télécharger un chart
helm pull <chart> --untar               # Télécharger et décompresser
helm package <chart-dir>                # Packager un chart
helm create <name>                      # Créer un nouveau chart
```

---

## Ressources et Liens Utiles

```bash
# Documentation officielle
https://helm.sh/docs/

# Artifact Hub (chercher des charts)
https://artifacthub.io/

# Helm Chart Repository
https://github.com/helm/charts

# Awesome Helm (liste de ressources)
https://github.com/cdwv/awesome-helm

# Helm Plugins
https://helm.sh/docs/community/related/

# Best Practices
https://helm.sh/docs/chart_best_practices/
```

---

## Exemples de Charts Populaires

### Nginx Ingress Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --set controller.service.type=LoadBalancer \
  --create-namespace -n ingress-nginx
```

### Cert-Manager (Let's Encrypt)
```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --set installCRDs=true \
  --create-namespace -n cert-manager
```

### Prometheus + Grafana (Monitoring)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --create-namespace -n monitoring
```

### PostgreSQL
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install my-postgres bitnami/postgresql \
  --set auth.postgresPassword=secretpassword \
  --set primary.persistence.size=10Gi
```

### Redis
```bash
helm install my-redis bitnami/redis \
  --set auth.password=secretpassword \
  --set master.persistence.size=8Gi
```

### GitLab
```bash
helm repo add gitlab https://charts.gitlab.io/
helm install gitlab gitlab/gitlab \
  --set global.hosts.domain=example.com \
  --set certmanager-issuer.email=admin@example.com
```

Voilà ! Vous avez maintenant un guide complet pour maîtriser Helm ! 🚀
