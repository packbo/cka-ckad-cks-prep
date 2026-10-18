# Raccourcis & Alias à créer - Setup Express Examen CKA

> **Le fichier le + important pour gagner du temps.** Copie-colle le bloc de setup
> au début de l'examen (2 minutes), puis utilise les alias tout le long.
> Chaque frappe économisée = des secondes cumulées sur 2 heures.

---

## Setup complet (À COPIER-COLLER AU DÉBUT DE L'EXAMEN)

Un seul bloc, prêt à coller dans le terminal :

```bash
# ===== ALIAS KUBECTL =====
alias k=kubectl
alias kgp='kubectl get pods'
alias kgpa='kubectl get pods -A'
alias kgs='kubectl get svc'
alias kgn='kubectl get nodes'
alias kgd='kubectl get deploy'
alias kgc='kubectl get cm'
alias kgsec='kubectl get secret'
alias kgns='kubectl get ns'
alias kgpv='kubectl get pv'
alias kgpvc='kubectl get pvc'
alias kd='kubectl describe'
alias kdel='kubectl delete'
alias kaf='kubectl apply -f'
alias kdf='kubectl delete -f'
alias kex='kubectl exec -it'
alias klog='kubectl logs'
alias kdf='kubectl delete -f'

# ===== EXPORTS (gain de temps massif) =====
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"

# ===== COMPLÉTION TAB =====
source <(kubectl completion bash)
complete -F __start_kubectl k

# ===== VIM (YAML lisible) =====
echo 'set ts=2 sw=2 et number' >> ~/.vimrc
```

---

## Les 2 exports qui changent tout

```bash
export do="--dry-run=client -o yaml"     # générer du YAML sans créer
export now="--force --grace-period=0"    # suppression immédiate
```

### `$do` — générer du YAML au lieu de l'écrire à la main
```bash
# Au lieu d'écrire un YAML de 30 lignes à la main :
k create deploy nginx --image=nginx --replicas=3 $do > deploy.yaml
k run busybox --image=busybox $do > pod.yaml
k expose pod nginx --port=80 --type=NodePort $do > svc.yaml
k create cm cfg --from-literal=k=v $do > cm.yaml
k create secret generic s --from-literal=p=secret $do > secret.yaml
k create sa mysa $do > sa.yaml
k create role r --verb=get,list --resource=pods $do > role.yaml

# Puis : vim deploy.yaml  →  k apply -f deploy.yaml
```

### `$now` — supprimer vite un pod bloqué
```bash
k delete pod bloqué $now        # suppression instantanée, sans attendre
```

---

## Alias par catégorie (avec exemples d'usage)

### Lecture rapide (`get`)
```bash
kgp                      # kubectl get pods
kgpa                     # kubectl get pods -A           (tous namespaces)
kgp -l app=nginx         # pods filtrés par label
kgn                      # kubectl get nodes
kgs                      # kubectl get svc
kgd                      # kubectl get deploy
kgns                     # kubectl get ns
k get all -A             # tout voir d'un coup
```

### Inspection (`describe`)
```bash
kd pod nginx             # kubectl describe pod nginx
kd deploy nginx
kd node node1
```

### Action (`apply` / `delete` / `exec`)
```bash
kaf deploy.yaml          # kubectl apply -f deploy.yaml
kdf deploy.yaml          # kubectl delete -f deploy.yaml
kex nginx -- sh          # kubectl exec -it nginx -- sh
klog nginx               # kubectl logs nginx
klog nginx --previous    # logs avant crash
```

---

## Raccourcis de génération YAML (à connaître par cœur)

| Ressource | Commande |
|-----------|----------|
| Pod | `k run X --image=img $do` |
| Deployment | `k create deploy X --image=img --replicas=3 $do` |
| Service ClusterIP | `k expose pod X --port=80 $do` |
| Service NodePort | `k expose pod X --port=80 --type=NodePort $do` |
| ConfigMap | `k create cm X --from-literal=k=v $do` |
| Secret | `k create secret generic X --from-literal=k=v $do` |
| ServiceAccount | `k create sa X $do` |
| Role | `k create role X --verb=get,list --resource=pods $do` |
| RoleBinding | `k create rolebinding X --role=R --user=U $do` |
| Job | `k create job X --image=busybox $do` |
| CronJob | `k create cronjob X --image=busybox --schedule="*/5 * * * *" $do` |

---

## Aliases optionnels "power user" (si tu mémorises bien)

```bash
# Changer de namespace rapidement
alias kns='kubectl config set-context --current --namespace'

# Usage : kns dev      (passe dans le namespace dev)

# Context courant
alias kctx='kubectl config current-context'
alias kctxs='kubectl config get-contexts'

# Events triés (debug indispensable)
alias kev='kubectl get events --sort-by=.metadata.creationTimestamp'

# YAML d'une ressource existante (pour modifier via replace)
alias kgxy='kubectl get -o yaml'

# Suppression propre d'un pod de test
alias krmtest='kubectl delete pod tmp --force --grace-period=0'
```

### Usage typique de `kns` (le + rentable)
```bash
kns dev                   # bascule dans dev
kgp                       # pods de dev
kns default               # retour au default
```

---

## Fonctions shell utiles (à coller si temps disponible)

```bash
# Shell jetable pour tester (debug réseau, résolution DNS, curl)
kt() { kubectl run tmp --rm -it --image=busybox -- "$@"; }
# Usage : kt wget -O- mysvc:80
# Usage : kt nslookup mysvc

# Describe le 1er pod qui match un nom
kdesc() { kubectl describe pod $(kubectl get pods --no-headers | grep "$1" | head -1 | awk '{print $1}'); }
# Usage : kdesc nginx

# Lister les images de tous les pods d'un namespace
kimg() { kubectl get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[*].image; }
```

---

## Anti-sèche mentale : les 5 raccourcis à RETENIR absolument

Si tu ne retiens que 5 choses :
```bash
k           # au lieu de kubectl
$do         # génère le YAML au lieu d'écrire à la main
$now        # supprime un pod bloqué instantanément
kns <ns>    # change de namespace en 1 mot
kt <cmd>    # shell jetable de debug
```

---

## Vérification du setup (après copier-coller)

```bash
# Doit afficher : kubectl
type k

# Doit afficher : --dry-run=client -o yaml
echo $do

# Doit fonctionner (liste les pods)
kgp

# La complétion Tab doit marcher
k get pods <TAB><TAB>
```

> Si tout marche → tu es prêt à enchaîner les questions vite.
> Le setup se rentabilise dès la 2e question.
