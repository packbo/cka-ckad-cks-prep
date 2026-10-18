# Exercices Pratiques CKA

## EXERCICES PAR THÈME

### 1. Pods Basiques

**Ex 1:** Créer un pod nginx avec label `app=web` dans namespace `prod`
```bash
k create ns prod
k run nginx --image=nginx --labels=app=web -n prod
```

**Ex 2:** Créer un pod busybox qui exécute la commande `sleep 3600`
```bash
k run busybox --image=busybox -- sleep 3600
```

**Ex 3:** Créer un pod avec 2 containers (nginx et busybox)
```bash
k run multi --image=nginx $do > pod.yaml
# Éditer et ajouter 2ème container
vim pod.yaml
```

### 2. Deployments & Services

**Ex 4:** Créer deployment `webapp` avec image `nginx:1.19`, 3 replicas
```bash
k create deploy webapp --image=nginx:1.19 --replicas=3
```

**Ex 5:** Exposer le deployment via service NodePort sur port 80
```bash
k expose deploy webapp --port=80 --type=NodePort
```

**Ex 6:** Scaler le deployment à 5 replicas
```bash
k scale deploy webapp --replicas=5
```

**Ex 7:** Update image du deployment à `nginx:1.20`
```bash
k set image deploy/webapp nginx=nginx:1.20
```

**Ex 8:** Rollback le deployment
```bash
k rollout undo deploy/webapp
```

### 3. ConfigMaps & Secrets

**Ex 9:** Créer ConfigMap `app-config` avec `DB_HOST=mysql` et `DB_PORT=3306`
```bash
k create cm app-config --from-literal=DB_HOST=mysql --from-literal=DB_PORT=3306
```

**Ex 10:** Créer Secret `db-secret` avec `password=secret123`
```bash
k create secret generic db-secret --from-literal=password=secret123
```

**Ex 11:** Créer pod qui utilise le ConfigMap comme variables d'environnement
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: nginx
    envFrom:
    - configMapRef:
        name: app-config
```

### 4. Persistent Volumes

**Ex 12:** Créer PV `pv-data` de 2Gi, accessMode `ReadWriteOnce`, hostPath `/data`
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-data
spec:
  capacity:
    storage: 2Gi
  accessModes:
  - ReadWriteOnce
  hostPath:
    path: /data
```

**Ex 13:** Créer PVC `pvc-data` demandant 1Gi
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-data
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

**Ex 14:** Créer pod utilisant le PVC monté sur `/data`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: pvc-data
```

### 5. RBAC

**Ex 15:** Créer ServiceAccount `app-sa`
```bash
k create sa app-sa
```

**Ex 16:** Créer Role `pod-reader` qui peut `get, list, watch` les pods
```bash
k create role pod-reader --verb=get,list,watch --resource=pods
```

**Ex 17:** Bind le role à la ServiceAccount
```bash
k create rolebinding pod-reader-binding --role=pod-reader --serviceaccount=default:app-sa
```

**Ex 18:** Créer pod utilisant cette ServiceAccount
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: nginx
```

### 6. Scheduling

**Ex 19:** Label node `node1` avec `disktype=ssd`
```bash
k label node node1 disktype=ssd
```

**Ex 20:** Créer pod qui doit tourner sur ce node (nodeSelector)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  nodeSelector:
    disktype: ssd
  containers:
  - name: app
    image: nginx
```

**Ex 21:** Taint node `node1` avec `env=prod:NoSchedule`
```bash
k taint node node1 env=prod:NoSchedule
```

**Ex 22:** Créer pod avec toleration pour ce taint
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  tolerations:
  - key: env
    operator: Equal
    value: prod
    effect: NoSchedule
  containers:
  - name: app
    image: nginx
```

### 7. Network Policies

**Ex 23:** Créer NetworkPolicy qui permet SEULEMENT les pods avec label `role=frontend` d'accéder aux pods `role=db` sur port 3306

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-policy
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
```

### 8. Troubleshooting Scenarios

**Scénario 1:** Pod en status `ImagePullBackOff`
```bash
# Diagnostic
k describe pod mypod  # Voir l'erreur dans Events

# Solution: corriger l'image name
k edit pod mypod
# OU
k delete pod mypod
k run mypod --image=correct-image
```

**Scénario 2:** Service ne répond pas
```bash
# 1. Vérifier endpoints
k get endpoints myservice

# 2. Si vide, vérifier labels
k get pods --show-labels
k describe svc myservice  # Voir selector

# 3. Corriger les labels
k label pod mypod app=correct-label
```

**Scénario 3:** Node NotReady
```bash
# 1. SSH sur le node
ssh node1

# 2. Vérifier kubelet
systemctl status kubelet
journalctl -u kubelet -f

# 3. Vérifier config
cat /var/lib/kubelet/config.yaml

# 4. Redémarrer
systemctl restart kubelet
```

**Scénario 4:** Pod en CrashLoopBackOff
```bash
# Voir les logs du crash
k logs mypod --previous

# Vérifier la commande
k describe pod mypod

# Fix: corriger la commande dans le YAML
```

### 9. Cluster Maintenance

**Ex 24:** Drain node pour maintenance
```bash
k drain node1 --ignore-daemonsets --delete-emptydir-data
```

**Ex 25:** Marquer node comme non-schedulable (sans éviction)
```bash
k cordon node1
```

**Ex 26:** Rendre node schedulable à nouveau
```bash
k uncordon node1
```

### 10. Mixed Scenarios (Type Examen)

**Scénario A:** Créer deployment `web` (nginx:1.19, 3 replicas) avec service ClusterIP sur port 80, dans namespace `production`
```bash
k create ns production
k create deploy web --image=nginx:1.19 --replicas=3 -n production
k expose deploy web --port=80 -n production
```

**Scénario B:** Créer pod `logger` qui écrit dans un volume, et pod `reader` qui lit depuis le même volume (shared volume)
```yaml
# Utiliser PVC ou emptyDir + hostPath
# 1. Créer PVC
# 2. Créer les 2 pods utilisant le même PVC avec accessMode ReadWriteMany
```

**Scénario C:** Le pod `app` ne peut pas se connecter à `db-service`. Debugger.
```bash
# 1. Vérifier que le service existe
k get svc db-service

# 2. Vérifier endpoints
k get endpoints db-service

# 3. Tester connectivity depuis app
k exec app -- nc -zv db-service 3306

# 4. Vérifier NetworkPolicy
k get netpol
```

## TIPS POUR L'EXAMEN

### 1. Gestion du Temps (2h = 120 min pour ~17 questions)

- Question facile (Pod, Deployment): **3-5 min**
- Question moyenne (RBAC, Storage): **7-10 min**
- Question difficile (NetworkPolicy, Troubleshooting): **10-15 min**

**Stratégie:**
1. Première passe (60 min): faire toutes les questions faciles
2. Deuxième passe (40 min): questions moyennes
3. Troisième passe (20 min): questions difficiles flaggées

### 2. Commandes à Connaître PAR COEUR

```bash
# Top 10 commandes
k run
k create deploy
k expose
k scale
k set image
k create cm/secret
k create role/rolebinding
k label
k taint
k drain/cordon/uncordon
```

### 3. Patterns YAML à Mémoriser

**initContainer:**
```yaml
spec:
  initContainers:
  - name: init
    image: busybox
    command: ['sh', '-c', 'echo init']
  containers:
  - name: app
    image: nginx
```

**resources:**
```yaml
spec:
  containers:
  - name: app
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

**securityContext:**
```yaml
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
  containers:
  - name: app
    securityContext:
      capabilities:
        add: ["NET_ADMIN"]
```

### 4. Erreurs Communes à ÉVITER

- ❌ Oublier de changer de context
- ❌ Travailler dans le mauvais namespace
- ❌ Écrire YAML à la main (utiliser `$do`)
- ❌ Oublier d'appliquer les changements (`k apply -f`)
- ❌ Ne pas vérifier que ça marche (`k get`)
- ❌ Bloquer sur une question (flag et continuer!)

### 5. Checklist Avant de Soumettre une Question

- [ ] Context correct? `k config current-context`
- [ ] Namespace correct? `k config view --minify | grep namespace`
- [ ] Ressource créée? `k get <resource>`
- [ ] Status OK? `k describe <resource>` (pas d'erreur dans Events)
- [ ] Teste fonctionnel? (ex: curl service, exec dans pod)

### 6. Raccourcis Vim Utiles

```vim
# Copier ligne
yy

# Coller
p

# Undo
u

# Redo
Ctrl+r

# Delete ligne
dd

# Indent ligne
>>

# Unindent
<<

# Visual mode
v (sélection) puis >> pour indenter block

# Go to line
:23 (aller ligne 23)

# Search
/mot (chercher "mot")
n (next occurrence)
```

## SIMULATION EXAMEN

Essayez de faire ces 5 questions en 30 minutes:

1. Créer namespace `exam`, créer deployment `web` (nginx, 2 replicas), exposer via NodePort (5 min)
2. Créer PV 1Gi hostPath `/data`, PVC 500Mi, pod utilisant ce PVC sur `/app/data` (7 min)
3. Créer Role permettant `get,list` pods et deployments, binder à user `john` (5 min)
4. Label node `node01` avec `type=worker`, créer pod avec nodeSelector vers ce label (4 min)
5. Debugger: service `broken-svc` ne marche pas, corriger le selector (4 min)

**Temps total:** 25 min + 5 min vérification = 30 min

Bonne chance pour votre CKA! 🚀
