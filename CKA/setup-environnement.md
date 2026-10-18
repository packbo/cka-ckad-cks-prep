# Setup Environnement CKA

## Configuration AVANT de commencer l'examen

### 1. Alias Essentiels
```bash
# Toujours mettre au début de chaque session
alias k=kubectl
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgn='kubectl get nodes'
alias kd='kubectl describe'
alias kdel='kubectl delete'
alias kaf='kubectl apply -f'
alias kex='kubectl exec -it'
alias klog='kubectl logs'

# Completion pour k aussi
complete -F __start_kubectl k

# Export pour gagner du temps
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"
```

### 2. Configuration VIM (~/.vimrc)
```vim
set tabstop=2
set shiftwidth=2
set expandtab
set number
set autoindent
set paste
```

**Raccourci dans l'examen:**
```bash
echo 'set tabstop=2 shiftwidth=2 expandtab' >> ~/.vimrc
```

### 3. Configuration kubectl

```bash
# Context et namespace rapide
kubectl config set-context --current --namespace=<namespace>

# Voir le context actuel
kubectl config current-context

# Changer de context (TRÈS IMPORTANT dans l'examen!)
kubectl config use-context <nom-context>
```

### 4. Commandes de génération YAML (NE PAS ÉCRIRE À LA MAIN)

```bash
# Pod
k run nginx --image=nginx $do > pod.yaml

# Deployment
k create deploy nginx --image=nginx --replicas=3 $do > deploy.yaml

# Service ClusterIP
k expose pod nginx --port=80 --target-port=80 $do > svc.yaml

# Service NodePort
k expose pod nginx --port=80 --target-port=80 --type=NodePort $do > svc-np.yaml

# Job
k create job test --image=busybox $do > job.yaml

# CronJob
k create cronjob test --image=busybox --schedule="*/5 * * * *" $do > cj.yaml

# ConfigMap
k create cm myconfig --from-literal=key=value $do > cm.yaml

# Secret
k create secret generic mysecret --from-literal=password=secret $do > secret.yaml

# ServiceAccount
k create sa mysa $do > sa.yaml
```

### 5. Best Practices Pendant l'Examen

**TOUJOURS:**
- Vérifier le context AVANT chaque question: `kubectl config current-context`
- Utiliser `$do` pour générer YAML au lieu d'écrire à la main
- Utiliser Tab completion
- Utiliser `k explain <resource>` pour vérifier les champs

**JAMAIS:**
- Ne pas écrire YAML à la main si possible
- Ne pas oublier de changer de context entre questions
- Ne pas perdre du temps sur une question bloquée (flag et revenir plus tard)

### 6. Navigation Rapide Documentation

Dans l'examen, vous avez accès à kubernetes.io. Utilisez la RECHERCHE:
- "pod spec" → trouver les champs de Pod
- "pv examples" → exemples de PersistentVolume
- "network policy" → exemples de NetworkPolicy

**Raccourci navigateur:** Ctrl+F pour chercher dans la page

### 7. Commandes de Debug Rapide

```bash
# Voir les events
k get events --sort-by=.metadata.creationTimestamp

# Voir les logs d'un pod
k logs <pod-name>
k logs <pod-name> -c <container-name>  # multi-container
k logs <pod-name> --previous  # logs du container précédent (crashed)

# Exec dans un pod
k exec -it <pod-name> -- /bin/sh

# Voir YAML complet d'une ressource existante
k get pod <name> -o yaml

# Vérifier rapidement
k get all -A  # Tout voir dans tous les namespaces
```

### 8. Checklist Début d'Examen (2 minutes)

```bash
# 1. Setup alias
alias k=kubectl
complete -F __start_kubectl k
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"

# 2. Setup vim
echo 'set tabstop=2 shiftwidth=2 expandtab' >> ~/.vimrc

# 3. Vérifier cluster
k get nodes
k config get-contexts
```

### 9. Time Management

- **Lire TOUTES les questions d'abord** (5 min)
- Faire les questions faciles d'abord (pods, deployments)
- **Flag** les questions difficiles (networking, troubleshooting)
- Garder 30 min à la fin pour revenir sur les questions difficiles
- **TOUJOURS vérifier** que la ressource est bien créée (`k get ...`)
