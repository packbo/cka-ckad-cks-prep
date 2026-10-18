# Scénarios Avancés et Outils Complémentaires CKA

## SCÉNARIOS COMPLEXES TYPE EXAMEN

### Scénario 1: Application Multi-Tier avec Persistance

**Mission:** Déployer une application web qui se connecte à une base de données

```bash
# 1. Namespace
k create ns app

# 2. Database avec PV
cat <<EOF | k apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
spec:
  capacity:
    storage: 2Gi
  accessModes:
  - ReadWriteOnce
  hostPath:
    path: /data/mysql
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
  namespace: app
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: app
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=  # password123 en base64
---
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  namespace: app
  labels:
    app: mysql
spec:
  containers:
  - name: mysql
    image: mysql:5.7
    env:
    - name: MYSQL_ROOT_PASSWORD
      valueFrom:
        secretKeyRef:
          name: mysql-secret
          key: password
    volumeMounts:
    - name: data
      mountPath: /var/lib/mysql
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: mysql-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mysql-service
  namespace: app
spec:
  selector:
    app: mysql
  ports:
  - port: 3306
EOF

# 3. Frontend deployment
k create deploy frontend --image=nginx --replicas=2 -n app
k expose deploy frontend --port=80 --type=NodePort -n app
```

### Scénario 2: Sécurité avec NetworkPolicy

**Mission:** Isoler les pods pour que seul frontend puisse parler à backend

```bash
# 1. Créer les apps
k create deploy frontend --image=nginx --replicas=2
k label deploy frontend tier=frontend

k create deploy backend --image=nginx --replicas=2
k label deploy backend tier=backend

# 2. NetworkPolicy pour backend
cat <<EOF | k apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
spec:
  podSelector:
    matchLabels:
      tier: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: frontend
    ports:
    - protocol: TCP
      port: 80
EOF

# 3. Tester depuis pod temporaire (devrait échouer)
k run test --image=busybox -it --rm -- wget -O- backend-service:80
```

### Scénario 3: Scheduling Avancé - Affinity

**Mission:** Déployer frontend sur nodes avec SSD, backend sur nodes différents du frontend

```bash
# 1. Label nodes
k label node node1 disktype=ssd
k label node node2 disktype=ssd

# 2. Frontend avec Node Affinity
cat <<EOF | k apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: disktype
                operator: In
                values:
                - ssd
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: backend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: frontend
        image: nginx
EOF
```

### Scénario 4: Init Containers

**Mission:** Attendre que le service DB soit up avant de démarrer l'app

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  initContainers:
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nslookup mysql-service; do echo waiting for db; sleep 2; done']
  containers:
  - name: app
    image: nginx
    env:
    - name: DB_HOST
      value: mysql-service
```

### Scénario 5: Resource Limits & QoS

**Mission:** Garantir resources pour app critique

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  containers:
  - name: app
    image: nginx
    resources:
      requests:
        memory: "128Mi"
        cpu: "500m"
      limits:
        memory: "256Mi"
        cpu: "1000m"
```

**QoS Classes:**
- **Guaranteed:** requests = limits (highest priority)
- **Burstable:** requests < limits
- **BestEffort:** pas de requests/limits (lowest priority)

### Scénario 6: Cluster Upgrade Complet

**Mission:** Upgrader cluster de v1.27 à v1.28

```bash
# MASTER NODE
# 1. Vérifier version actuelle
k get nodes

# 2. Drain master
k drain controlplane --ignore-daemonsets

# 3. Upgrade kubeadm
apt-mark unhold kubeadm
apt-get update
apt-get install -y kubeadm=1.28.0-00
apt-mark hold kubeadm

# 4. Vérifier plan
kubeadm upgrade plan

# 5. Upgrade
kubeadm upgrade apply v1.28.0

# 6. Upgrade kubelet & kubectl
apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
apt-mark hold kubelet kubectl

# 7. Restart
systemctl daemon-reload
systemctl restart kubelet

# 8. Uncordon
k uncordon controlplane

# WORKER NODES (pour chaque worker)
# Sur master
k drain node1 --ignore-daemonsets --delete-emptydir-data

# Sur worker
apt-mark unhold kubeadm
apt-get update
apt-get install -y kubeadm=1.28.0-00
apt-mark hold kubeadm

kubeadm upgrade node

apt-mark unhold kubelet kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
apt-mark hold kubelet kubectl

systemctl daemon-reload
systemctl restart kubelet

# Sur master
k uncordon node1
```

### Scénario 7: ETCD Backup & Disaster Recovery

**Mission:** Sauvegarder et restaurer etcd

```bash
# BACKUP
# 1. Trouver les certificats
k -n kube-system describe pod etcd-controlplane | grep -E 'cert|key|trusted'

# 2. Backup
ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 3. Vérifier backup
ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-backup.db

# RESTORE
# 1. Restore dans nouveau directory
ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-backup.db \
  --data-dir=/var/lib/etcd-backup

# 2. Modifier etcd manifest
vim /etc/kubernetes/manifests/etcd.yaml
# Changer hostPath de volume de /var/lib/etcd à /var/lib/etcd-backup

# 3. Wait for etcd pod restart
k -n kube-system get pods | grep etcd
```

### Scénario 8: Broken Cluster - Kubelet Down

**Mission:** Node est NotReady, fixer kubelet

```bash
# 1. Diagnostic
k get nodes  # node1 NotReady

# 2. SSH sur node
ssh node1

# 3. Check kubelet
systemctl status kubelet  # failed

# 4. Voir logs
journalctl -u kubelet -f

# Cas fréquents:
# - Config path incorrect dans service
# - Certificate expiré
# - Port déjà utilisé

# 5. Check config
cat /var/lib/kubelet/config.yaml

# 6. Check service
cat /etc/systemd/system/kubelet.service.d/10-kubeadm.conf

# 7. Fix et restart
systemctl daemon-reload
systemctl restart kubelet
systemctl enable kubelet

# 8. Vérifier
systemctl status kubelet
```

### Scénario 9: Service Discovery Problem

**Mission:** Pods ne peuvent pas résoudre les services DNS

```bash
# 1. Test DNS depuis pod
k run test --image=busybox -it --rm -- nslookup kubernetes.default

# Si échec:
# 2. Vérifier coredns
k -n kube-system get pods | grep coredns
k -n kube-system logs coredns-xxxx

# 3. Vérifier coredns service
k -n kube-system get svc kube-dns
k -n kube-system describe svc kube-dns

# 4. Vérifier configmap
k -n kube-system get cm coredns -o yaml

# 5. Restart coredns si nécessaire
k -n kube-system rollout restart deploy coredns
```

## OUTILS COMPLÉMENTAIRES

### HELM (Pas dans CKA mais utile à connaître)

**Helm = Package manager pour Kubernetes**

```bash
# Installation Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Commandes de base
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo nginx
helm install my-nginx bitnami/nginx
helm list
helm uninstall my-nginx

# Créer son propre chart
helm create mychart
helm install myapp ./mychart
helm upgrade myapp ./mychart

# Template sans install (dry-run)
helm template myapp ./mychart
```

**Quand utiliser Helm:**
- Déploiement d'apps complexes (plusieurs resources)
- Réutilisation (même app dans dev/staging/prod)
- Versioning des déploiements

### KUSTOMIZE (Inclus dans kubectl, plus probable dans CKA)

**Kustomize = Personnalisation YAML sans templates**

```bash
# Structure
myapp/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml

# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- deployment.yaml
- service.yaml

# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
- ../../base
namePrefix: prod-
replicas:
- name: myapp
  count: 5

# Apply
k apply -k overlays/prod/

# Build (voir le YAML sans appliquer)
k kustomize overlays/prod/
```

**Avantages Kustomize:**
- Native dans kubectl (pas d'install)
- Pas de templating (pure YAML)
- Gestion multi-environnements

### KUBECTL PLUGINS

```bash
# Installer krew (plugin manager)
curl -fsSL https://krew.sigs.k8s.io/install | bash

# Plugins utiles
kubectl krew install ctx      # Changer context rapidement
kubectl krew install ns       # Changer namespace rapidement
kubectl krew install tree     # Voir hierarchie resources
kubectl krew install whoami   # Voir permissions actuelles

# Utilisation
kubectl ctx                   # Lister contexts
kubectl ctx prod             # Switch vers prod
kubectl ns dev               # Switch vers namespace dev
```

### KUBEADM (Essentiel pour CKA)

```bash
# Init cluster
kubeadm init --pod-network-cidr=10.244.0.0/16

# Join worker
kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>

# Generate join command
kubeadm token create --print-join-command

# Reset node
kubeadm reset

# Upgrade
kubeadm upgrade plan
kubeadm upgrade apply v1.28.0
```

### CRICTL (Container Runtime CLI - Important pour CKA)

**Quand kubelet ou pods ne marchent pas, utiliser crictl**

```bash
# Lister containers
crictl ps
crictl ps -a  # inclus stopped

# Logs d'un container
crictl logs <container-id>

# Exec dans container
crictl exec -it <container-id> sh

# Inspecter
crictl inspect <container-id>

# Images
crictl images

# Pods
crictl pods

# Utile pour debug au niveau runtime
```

### JSONPATH & JQ (Manipulation données)

```bash
# JSONPATH
# Get node IPs
k get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}'

# Get pod images
k get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# Custom columns
k get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP

# JQ (si installé)
k get pods -o json | jq '.items[].spec.containers[].image'
```

## POINTS CLÉS À RETENIR

### Ce qui EST dans le CKA:
- ✅ kubectl, kubeadm, crictl
- ✅ Kustomize (via kubectl -k)
- ✅ YAML editing
- ✅ Troubleshooting cluster components
- ✅ Networking (CNI concepts)
- ✅ Storage (PV, PVC)
- ✅ Security (RBAC, NetworkPolicy)
- ✅ Cluster upgrade
- ✅ ETCD backup/restore

### Ce qui N'EST PAS dans le CKA:
- ❌ Helm
- ❌ CI/CD tools
- ❌ Monitoring (Prometheus, Grafana)
- ❌ Service Mesh (Istio)
- ❌ Development (coding apps)

### Focus pour l'examen:
1. **Speed:** générer YAML automatiquement
2. **Documentation:** savoir chercher sur kubernetes.io
3. **Troubleshooting:** logs, describe, events
4. **Context switching:** TOUJOURS vérifier le context
5. **Verification:** TOUJOURS tester que ça marche

## DERNIERS CONSEILS

### Avant l'examen (1 semaine avant):
- [ ] Faire 50+ exercices pratiques
- [ ] Savoir upgrader un cluster en <15 min
- [ ] Mémoriser les alias et setup vim
- [ ] Pratiquer avec chronomètre
- [ ] Réviser troubleshooting scenarios

### Le jour J:
- [ ] Avoir bu du café ☕
- [ ] Avoir une pièce calme
- [ ] Tester webcam/micro
- [ ] Avoir une pièce d'identité
- [ ] Commencer 15 min en avance

### Pendant l'examen:
- [ ] Setup alias immédiatement (2 min)
- [ ] Lire toutes les questions (5 min)
- [ ] Faire les faciles d'abord
- [ ] Flag les difficiles
- [ ] Garder 30 min pour réviser

**Score pour passer:** 66%
**Durée:** 2 heures
**Questions:** ~15-20
**Retake:** 1 gratuit si échec

Vous êtes prêt! 💪
