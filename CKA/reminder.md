# CKA Reminder - Concepts et Commandes Essentiels

## 1. PODS

### Création
```bash
# Simple
k run nginx --image=nginx

# Avec variables d'environnement
k run nginx --image=nginx --env="VAR=value"

# Avec labels
k run nginx --image=nginx --labels="app=web,tier=frontend"

# Avec port
k run nginx --image=nginx --port=80

# Commande custom
k run busybox --image=busybox -- sleep 3600
```

### Multi-container Pod
```yaml
# k run ne peut pas faire multi-container, utiliser template:
apiVersion: v1
kind: Pod
metadata:
  name: multi
spec:
  containers:
  - name: nginx
    image: nginx
  - name: busybox
    image: busybox
    command: ['sleep', '3600']
```

### Pod avec volume
```yaml
spec:
  containers:
  - name: nginx
    image: nginx
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    emptyDir: {}
```

## 2. DEPLOYMENTS

```bash
# Créer
k create deploy nginx --image=nginx --replicas=3

# Scale
k scale deploy nginx --replicas=5

# Update image
k set image deploy/nginx nginx=nginx:1.19

# Rollout status
k rollout status deploy/nginx

# Rollout history
k rollout history deploy/nginx

# Rollback
k rollout undo deploy/nginx
k rollout undo deploy/nginx --to-revision=2

# Autoscale
k autoscale deploy nginx --min=2 --max=10 --cpu-percent=80
```

## 3. SERVICES

```bash
# ClusterIP (par défaut)
k expose pod nginx --port=80 --target-port=80

# NodePort
k expose pod nginx --port=80 --type=NodePort

# Créer directement
k create svc clusterip mysvc --tcp=80:8080
k create svc nodeport mysvc --tcp=80:8080 --node-port=30080
```

### Service YAML (copier depuis kubernetes.io)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: nginx  # IMPORTANT: doit matcher les labels du Pod
  ports:
  - protocol: TCP
    port: 80        # Port du service
    targetPort: 80  # Port du container
  type: ClusterIP
```

## 4. NAMESPACES

```bash
# Créer
k create ns dev

# Changer de namespace par défaut
k config set-context --current --namespace=dev

# Lister tout dans tous les namespaces
k get pods -A
k get all -A
```

## 5. CONFIGMAPS & SECRETS

### ConfigMap
```bash
# From literal
k create cm myconfig --from-literal=key1=value1 --from-literal=key2=value2

# From file
k create cm myconfig --from-file=app.properties

# Utiliser dans Pod
spec:
  containers:
  - name: app
    envFrom:
    - configMapRef:
        name: myconfig
```

### Secret
```bash
# From literal
k create secret generic mysecret --from-literal=password=secret123

# Utiliser dans Pod
spec:
  containers:
  - name: app
    env:
    - name: PASSWORD
      valueFrom:
        secretKeyRef:
          name: mysecret
          key: password
```

## 6. PERSISTENT VOLUMES

### PersistentVolume (créé par admin)
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-1
spec:
  capacity:
    storage: 1Gi
  accessModes:
  - ReadWriteOnce
  hostPath:
    path: /data/pv-1
```

### PersistentVolumeClaim (créé par user)
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-1
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
```

### Utiliser PVC dans Pod
```yaml
spec:
  containers:
  - name: app
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: pvc-1
```

## 7. RBAC (Role-Based Access Control)

### Role (dans namespace)
```bash
# Créer Role
k create role pod-reader --verb=get,list,watch --resource=pods
```

### RoleBinding
```bash
# Bind Role à User
k create rolebinding pod-reader-binding --role=pod-reader --user=john

# Bind Role à ServiceAccount
k create rolebinding pod-reader-binding --role=pod-reader --serviceaccount=default:mysa
```

### ClusterRole (cluster-wide)
```bash
k create clusterrole pod-reader --verb=get,list,watch --resource=pods
k create clusterrolebinding pod-reader-binding --clusterrole=pod-reader --user=john
```

### ServiceAccount
```bash
k create sa mysa

# Utiliser dans Pod
spec:
  serviceAccountName: mysa
```

## 8. NETWORK POLICY

**Copier exemple depuis kubernetes.io/docs/concepts/services-networking/network-policies/**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-network-policy
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
```

**Concept:**
- Par défaut: tout est ouvert
- Dès qu'une NetworkPolicy s'applique: tout est fermé sauf ce qui est autorisé
- Utiliser `podSelector` pour cibler les pods
- `ingress`: qui peut accéder AU pod
- `egress`: où le pod peut accéder

## 9. TAINTS & TOLERATIONS

### Taints (sur Nodes)
```bash
# Ajouter taint
k taint node node1 key=value:NoSchedule

# Enlever taint (avec -)
k taint node node1 key=value:NoSchedule-
```

### Tolerations (dans Pod)
```yaml
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
```

**Effets:**
- `NoSchedule`: pas de nouveaux pods
- `PreferNoSchedule`: éviter si possible
- `NoExecute`: éviction des pods existants

## 10. NODE SELECTOR & AFFINITY

### Node Selector (simple)
```bash
# Label node
k label node node1 disktype=ssd

# Dans Pod
spec:
  nodeSelector:
    disktype: ssd
```

### Node Affinity (avancé)
```yaml
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
```

## 11. STATIC PODS

**Location:** `/etc/kubernetes/manifests/`

```bash
# Créer static pod: copier YAML dans ce dossier
cp pod.yaml /etc/kubernetes/manifests/

# Le kubelet va automatiquement créer le pod
```

**Reconnaître:** nom du pod = `<nom>-<nom-node>`

## 12. DAEMON SETS

```bash
# Créer DaemonSet (pas de commande directe, utiliser deployment et modifier)
k create deploy nginx --image=nginx $do > ds.yaml
# Puis modifier kind: DaemonSet et enlever replicas
```

**Concept:** Un pod par node (monitoring, logging, network)

## 13. JOBS & CRONJOBS

### Job
```bash
k create job test --image=busybox -- echo "Hello"
```

### CronJob
```bash
k create cronjob test --image=busybox --schedule="*/5 * * * *" -- echo "Hello"
```

## 14. UPGRADE CLUSTER

### Master Node
```bash
# 1. Drain
k drain controlplane --ignore-daemonsets

# 2. Upgrade kubeadm
apt-get update
apt-get install -y kubeadm=1.28.0-00

# 3. Plan upgrade
kubeadm upgrade plan

# 4. Apply upgrade
kubeadm upgrade apply v1.28.0

# 5. Upgrade kubelet et kubectl
apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
systemctl daemon-reload
systemctl restart kubelet

# 6. Uncordon
k uncordon controlplane
```

### Worker Node
```bash
# Sur master: drain le worker
k drain node1 --ignore-daemonsets

# Sur worker node:
apt-get update
apt-get install -y kubeadm=1.28.0-00
kubeadm upgrade node
apt-get install -y kubelet=1.28.0-00
systemctl daemon-reload
systemctl restart kubelet

# Sur master: uncordon
k uncordon node1
```

## 15. BACKUP & RESTORE ETCD

### Backup
```bash
ETCDCTL_API=3 etcdctl snapshot save /tmp/snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

### Restore
```bash
ETCDCTL_API=3 etcdctl snapshot restore /tmp/snapshot.db \
  --data-dir=/var/lib/etcd-backup
```

**Trouver les certificats:**
```bash
k -n kube-system describe pod etcd-controlplane | grep -E 'cert|key|trusted'
```

## 16. TROUBLESHOOTING

### Pod ne démarre pas
```bash
# 1. Voir status
k get pod mypod

# 2. Describe pour events
k describe pod mypod

# 3. Logs
k logs mypod
k logs mypod -c container-name  # si multi-container
k logs mypod --previous  # si crashed

# 4. Exec pour debug
k exec -it mypod -- /bin/sh
```

### Service ne marche pas
```bash
# 1. Vérifier endpoints
k get endpoints myservice

# 2. Vérifier labels
k get pods --show-labels
k describe svc myservice  # voir le selector

# 3. Test depuis un pod temporaire
k run test --image=busybox -it --rm -- wget -O- myservice:80
```

### Node not ready
```bash
# 1. Voir status
k get nodes
k describe node node1

# 2. SSH sur node et vérifier kubelet
systemctl status kubelet
journalctl -u kubelet

# 3. Redémarrer si nécessaire
systemctl restart kubelet
```

## 17. COMMANDES EXPLAIN (votre meilleur ami!)

```bash
# Voir les champs disponibles
k explain pod
k explain pod.spec
k explain pod.spec.containers
k explain deployment.spec

# Très utile quand vous oubliez un champ!
k explain pod.spec.volumes
k explain pod.spec.securityContext
```

## 18. JSONPATH (pour filtrer output)

```bash
# Obtenir tous les noms de pods
k get pods -o jsonpath='{.items[*].metadata.name}'

# Obtenir les images des containers
k get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# Custom columns
k get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

## STRATÉGIE GÉNÉRALE

1. **Lire la question 2 fois** - comprendre ce qui est demandé
2. **Vérifier le context** - `k config current-context`
3. **Vérifier le namespace** - `k config view --minify | grep namespace`
4. **Générer YAML** - utiliser `k create/run` avec `$do`
5. **Modifier si nécessaire** - vim, copier-coller depuis kubernetes.io
6. **Apply** - `k apply -f file.yaml`
7. **Vérifier** - `k get`, `k describe`
8. **Next question** - ne pas bloquer!

## RESOURCES KUBERNETES.IO À CONNAÎTRE

- **Cheat Sheet:** kubernetes.io/docs/reference/kubectl/cheatsheet/
- **Pod:** kubernetes.io/docs/concepts/workloads/pods/
- **Network Policies:** kubernetes.io/docs/concepts/services-networking/network-policies/
- **Persistent Volumes:** kubernetes.io/docs/concepts/storage/persistent-volumes/
- **RBAC:** kubernetes.io/docs/reference/access-authn-authz/rbac/

**Astuce:** Utilisez Ctrl+F dans la documentation pour chercher des exemples!
