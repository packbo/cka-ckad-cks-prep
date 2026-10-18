# Commandes Kubernetes et Linux Avancées

## Manipulation des Namespaces

### Lister les namespaces avec formatage personnalisé
```bash
# Liste simple séparée par des virgules
kubectl get ns -o jsonpath='{range .items[*]}{.metadata.name}{","}{end}' | sed 's/,$//'

# Sans kube-system
kubectl get ns -o json | jq -r '.items[].metadata.name | select(. != "kube-system")' | paste -sd ','

# Sans les namespaces système (kube-*)
kubectl get ns -o json | jq -r '.items[].metadata.name | select(startswith("kube-") | not)' | paste -sd ','

# Avec awk (alternative)
kubectl get ns --no-headers | awk '{print $1}' | grep -v kube-system | paste -sd ','

# Exclure plusieurs namespaces
kubectl get ns -o json | jq -r '.items[].metadata.name | select(. != "kube-system" and . != "kube-public")' | paste -sd ','
```

## Découvrir la structure JSON/YAML

### Voir la structure complète en JSON
```bash
# Pour n'importe quelle ressource
kubectl get pod mon-pod -o json
kubectl get deployment mon-deploy -o json
kubectl get svc mon-service -o json

# Avec jq pour une structure lisible
kubectl get pod mon-pod -o json | jq '.'

# Voir seulement les clés de premier niveau
kubectl get pod mon-pod -o json | jq 'keys'

# Explorer la structure imbriquée
kubectl get pod mon-pod -o json | jq '.metadata | keys'
kubectl get pod mon-pod -o json | jq '.spec | keys'
kubectl get pod mon-pod -o json | jq '.status | keys'

# Structure en YAML (plus lisible)
kubectl get pod mon-pod -o yaml

# Combiner avec yq pour explorer
kubectl get pod mon-pod -o yaml | yq e '.spec.containers[0]' -
```

### Trouver les chemins JSONPath
```bash
# Astuce : utiliser jq avec --raw-output pour tester
kubectl get pod mon-pod -o json | jq -r '.spec.containers[0].name'

# Puis convertir en JSONPath pour kubectl
kubectl get pod mon-pod -o jsonpath='{.spec.containers[0].name}'

# Afficher les chemins avec jq
kubectl get pod mon-pod -o json | jq 'paths(scalars) as $p | "\($p | join("."))"'

# Voir tous les chemins possibles
kubectl get pod mon-pod -o json | jq '[paths(scalars)] | map(join(".")) | .[]'
```

## Commandes JSONPath avancées

### Boucles et filtres
```bash
# Tous les pods avec leur node
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\n"}{end}'

# Pods avec leur IP
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.podIP}{"\n"}{end}'

# Conteneurs et leurs images
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.containers[*]}{.name}:{.image}{" "}{end}{"\n"}{end}'

# Filtrer avec conditions (limité dans JSONPath)
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'

# Resources requests/limits
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].resources.requests.memory}{"\n"}{end}'

# Labels en format clé=valeur
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .metadata.labels}{@}{end}{"\n"}{end}'
```

## JQ - Manipulation JSON avancée

### Installation et usage de base
```bash
# Vérifier si jq est installé
which jq
jq --version

# Installer jq (si nécessaire)
# Ubuntu/Debian:
sudo apt-get install jq
# RHEL/CentOS:
sudo yum install jq

# Syntaxe de base
kubectl get pods -o json | jq '.'                    # Formater
kubectl get pods -o json | jq '.items[0]'            # Premier élément
kubectl get pods -o json | jq '.items[] | .metadata.name'  # Tous les noms
```

### Exemples jq avancés
```bash
# Filtrer par condition
kubectl get pods -A -o json | jq '.items[] | select(.status.phase=="Running")'

# Multiples conditions (AND)
kubectl get pods -A -o json | jq '.items[] | select(.status.phase=="Running" and .metadata.namespace!="kube-system")'

# Conditions OR
kubectl get pods -A -o json | jq '.items[] | select(.status.phase=="Running" or .status.phase=="Pending")'

# Créer des objets personnalisés
kubectl get pods -A -o json | jq '.items[] | {name: .metadata.name, ns: .metadata.namespace, status: .status.phase}'

# Compter les éléments
kubectl get pods -A -o json | jq '[.items[] | select(.status.phase=="Running")] | length'

# Grouper par namespace
kubectl get pods -A -o json | jq 'group_by(.metadata.namespace) | map({namespace: .[0].metadata.namespace, count: length})'

# Trier
kubectl get pods -A -o json | jq '.items | sort_by(.metadata.creationTimestamp) | reverse'

# Sélectionner des champs spécifiques
kubectl get pods -A -o json | jq '.items[] | {pod: .metadata.name, image: .spec.containers[0].image, node: .spec.nodeName}'

# Trouver les pods sans limits
kubectl get pods -A -o json | jq '.items[] | select(.spec.containers[0].resources.limits == null) | .metadata.name'

# Extraire les variables d'environnement
kubectl get pod mon-pod -o json | jq '.spec.containers[0].env[] | "\(.name)=\(.value)"'

# Tableau de résumé
kubectl get pods -A -o json | jq -r '.items[] | [.metadata.namespace, .metadata.name, .status.phase] | @tsv'
```

## YQ - Manipulation YAML

### Installation et usage de base
```bash
# Vérifier yq
which yq
yq --version

# Installer yq (version mikefarah/yq recommandée)
# Binaire:
sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq
sudo chmod +x /usr/bin/yq

# Ou via snap:
sudo snap install yq

# Syntaxe de base
kubectl get pod mon-pod -o yaml | yq e '.spec.containers[0].name' -
kubectl get pod mon-pod -o yaml | yq e '.metadata.labels' -
```

### Exemples yq avancés
```bash
# Extraire des valeurs
kubectl get pod mon-pod -o yaml | yq e '.spec.containers[].image' -

# Modifier et sauvegarder
kubectl get deploy mon-deploy -o yaml | yq e '.spec.replicas = 5' - > deploy-modified.yaml

# Filtrer
kubectl get pods -o yaml | yq e '.items[] | select(.status.phase == "Running")' -

# Combiner plusieurs fichiers YAML
yq eval-all '. as $item ireduce ({}; . * $item)' file1.yaml file2.yaml

# Convertir YAML en JSON
kubectl get pod mon-pod -o yaml | yq e -o=json '.'

# Extraire tous les noms de conteneurs
kubectl get pods -o yaml | yq e '.items[].spec.containers[].name' -

# Créer un tableau
kubectl get pods -o yaml | yq e '[.items[].metadata.name]' -
```

## GREP avancé pour Kubernetes

### Recherche de patterns
```bash
# Chercher dans les logs
kubectl logs mon-pod | grep "ERROR"
kubectl logs mon-pod | grep -i "error"                    # Case insensitive
kubectl logs mon-pod | grep -E "ERROR|WARN"               # OR pattern
kubectl logs mon-pod | grep -v "DEBUG"                    # Exclure
kubectl logs mon-pod | grep -A 5 "ERROR"                  # 5 lignes après
kubectl logs mon-pod | grep -B 5 "ERROR"                  # 5 lignes avant
kubectl logs mon-pod | grep -C 5 "ERROR"                  # 5 lignes autour

# Compter les occurrences
kubectl logs mon-pod | grep -c "ERROR"

# Numéros de ligne
kubectl logs mon-pod | grep -n "ERROR"

# Chercher dans plusieurs pods
kubectl logs -l app=mon-app | grep "ERROR"

# Avec couleurs
kubectl logs mon-pod | grep --color=always "ERROR"

# Regex avancé
kubectl logs mon-pod | grep -E "error|exception|fail" -i
kubectl logs mon-pod | grep -P '\d{3}-\d{3}-\d{4}'        # Perl regex (numéros)
```

## AWK - Traitement de texte

### Exemples pratiques
```bash
# Extraire une colonne
kubectl get pods | awk '{print $1}'                       # Noms
kubectl get pods | awk '{print $3}'                       # Status
kubectl get pods | awk 'NR>1 {print $1}'                  # Sans header

# Colonnes multiples
kubectl get pods | awk '{print $1, $3}'
kubectl get pods | awk '{print $1"\t"$3}'                 # Avec tab

# Filtres conditionnels
kubectl get pods | awk '$3=="Running" {print $1}'
kubectl get pods | awk 'NR>1 && $3=="Running" {print $1}'

# Calculs
kubectl top nodes | awk 'NR>1 {sum+=$3} END {print sum}'  # Somme CPU%

# Formater la sortie
kubectl get pods | awk '{printf "%-30s %s\n", $1, $3}'

# Compter les lignes par condition
kubectl get pods -A | awk '$4=="Running" {count++} END {print count}'

# Extraire et joindre
kubectl get ns --no-headers | awk '{print $1}' | paste -sd ','
```

## SED - Édition de flux

### Substitutions
```bash
# Remplacer dans une sortie
kubectl get pods | sed 's/Running/OK/g'
kubectl get svc -o yaml | sed 's/ClusterIP/LoadBalancer/g'

# Supprimer des lignes
kubectl get pods | sed '/kube-system/d'                   # Supprimer ligne avec pattern
kubectl get pods | sed '1d'                               # Supprimer première ligne
kubectl get pods | sed '$d'                               # Supprimer dernière ligne

# Extraire des lignes
kubectl get pods | sed -n '2,5p'                          # Lignes 2 à 5
kubectl get pods | sed -n '/Running/p'                    # Lignes avec Running

# Modifications multiples
kubectl get pods | sed -e 's/Running/OK/' -e 's/Pending/WAIT/'

# Regex avancé
kubectl logs mon-pod | sed -n '/ERROR/,/^$/p'             # De ERROR à ligne vide
```

## JOURNALCTL - Logs système

### Commandes essentielles
```bash
# Logs de kubelet
journalctl -u kubelet -f                                  # Suivre en temps réel
journalctl -u kubelet --since "1 hour ago"
journalctl -u kubelet --since "2024-01-15 10:00:00"
journalctl -u kubelet --until "2024-01-15 11:00:00"

# Logs de containerd/docker
journalctl -u containerd -f
journalctl -u docker -f

# Filtrer par priorité
journalctl -u kubelet -p err                              # Erreurs seulement
journalctl -u kubelet -p warning                          # Warning et au-dessus

# Sortie JSON
journalctl -u kubelet -o json-pretty

# Dernières N lignes
journalctl -u kubelet -n 100
journalctl -u kubelet --no-pager | tail -100

# Combiner avec grep
journalctl -u kubelet --since "1 hour ago" | grep -i error

# Suivre plusieurs services
journalctl -u kubelet -u containerd -f

# Logs du boot
journalctl -b                                             # Boot actuel
journalctl -b -1                                          # Boot précédent

# Export
journalctl -u kubelet --since today > kubelet-logs.txt

# Avec plus de contexte
journalctl -u kubelet -o verbose
journalctl -u kubelet -o cat                              # Sans métadonnées

# Vider les logs
journalctl --vacuum-time=2d                               # Supprimer > 2 jours
journalctl --vacuum-size=500M                             # Garder max 500M
```

## WATCH - Surveillance en temps réel

```bash
# Surveillance continue
watch kubectl get pods
watch -n 2 kubectl get pods                               # Toutes les 2 secondes
watch -n 1 kubectl top nodes
watch -d kubectl get pods                                 # Highlight différences

# Combiné avec d'autres commandes
watch "kubectl get pods | grep Running | wc -l"
watch "kubectl top nodes --no-headers | awk '{print \$1, \$3}'"

# Surveiller plusieurs namespaces
watch kubectl get pods -A

# Avec filtres
watch "kubectl get events --sort-by='.lastTimestamp' | tail -20"
```

## XARGS - Exécution en masse

```bash
# Supprimer tous les pods Failed
kubectl get pods -A | grep Failed | awk '{print $1, $2}' | xargs -n2 kubectl delete pod -n

# Décrire tous les pods d'un namespace
kubectl get pods -n mon-ns --no-headers | awk '{print $1}' | xargs -I {} kubectl describe pod {} -n mon-ns

# Logs de tous les pods
kubectl get pods --no-headers | awk '{print $1}' | xargs -I {} kubectl logs {} --tail=10

# Restart de tous les deployments
kubectl get deploy --no-headers | awk '{print $1}' | xargs -I {} kubectl rollout restart deploy {}

# Parallel (avec -P)
kubectl get pods --no-headers | awk '{print $1}' | xargs -P 5 -I {} kubectl logs {} --tail=10
```

## COLUMN - Formater en colonnes

```bash
# Aligner en colonnes
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP | column -t

# Avec délimiteur personnalisé
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name},{.status.capacity.cpu},{.status.capacity.memory}{"\n"}{end}' | column -t -s ','

# Pipeline complet
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace},{.metadata.name},{.status.phase}{"\n"}{end}' | column -t -s ','
```

## SORT et UNIQ

```bash
# Trier les pods par nom
kubectl get pods --no-headers | sort

# Trier par colonne spécifique
kubectl get pods --no-headers | sort -k3                  # Par status

# Trier numériquement
kubectl top pods --no-headers | sort -k2 -n               # Par CPU
kubectl top pods --no-headers | sort -k2 -nr              # Décroissant

# Combiner avec uniq
kubectl get pods -A -o jsonpath='{.items[*].spec.nodeName}' | tr ' ' '\n' | sort | uniq
kubectl get pods -A -o jsonpath='{.items[*].spec.nodeName}' | tr ' ' '\n' | sort | uniq -c  # Avec compte

# Top 10 images utilisées
kubectl get pods -A -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort | uniq -c | sort -nr | head -10
```

## FIND - Recherche de fichiers

```bash
# Trouver tous les manifests YAML
find /home/pascal/Documents/courses/kubernetes -name "*.yaml"
find . -name "*.yaml" -o -name "*.yml"

# Fichiers modifiés récemment
find . -name "*.yaml" -mtime -1                           # Dernières 24h
find . -name "*.yaml" -mmin -60                           # Dernière heure

# Avec action
find . -name "*.yaml" -exec kubectl apply -f {} \;
find . -name "*.yaml" -exec grep -l "kind: Deployment" {} \;

# Par taille
find . -name "*.yaml" -size +1M                           # Plus de 1MB

# Exclure des répertoires
find . -name "*.yaml" -not -path "*/node_modules/*"
```

## Combinaisons puissantes

### Pipeline complexe - Pods triés par CPU
```bash
kubectl top pods -A --no-headers | \
  awk '{printf "%s\t%s\t%s\n", $1, $2, $3}' | \
  column -t | \
  sort -k3 -n
```

### Trouver les pods qui redémarrent beaucoup
```bash
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.status.containerStatuses[0].restartCount > 5) | "\(.metadata.namespace)/\(.metadata.name): \(.status.containerStatuses[0].restartCount) restarts"'
```

### Résumé des ressources par namespace
```bash
kubectl get pods -A -o json | \
  jq -r '.items[] | [.metadata.namespace, .spec.containers[0].resources.requests.cpu // "N/A", .spec.containers[0].resources.requests.memory // "N/A"] | @tsv' | \
  awk '{ns[$1]++} END {for (n in ns) print n, ns[n]}' | \
  column -t | \
  sort -k2 -nr
```

### Événements récents formatés
```bash
kubectl get events -A --sort-by='.lastTimestamp' | \
  tail -20 | \
  awk '{print $1, $5, $6, $7, $8, $9, $10}' | \
  column -t
```

### Audit des images sans tag latest
```bash
kubectl get pods -A -o json | \
  jq -r '.items[].spec.containers[] | select(.image | contains(":latest") | not) | .image' | \
  sort | \
  uniq -c | \
  sort -nr
```

## Outils supplémentaires utiles

### htop - Monitoring processus
```bash
htop                                                      # Interface interactive
htop -u kubelet                                           # Filtrer par user
```

### netstat/ss - Réseau
```bash
# Ports en écoute
netstat -tlnp | grep kubelet
ss -tlnp | grep kubelet

# Connexions établies
ss -tn | grep :6443                                       # API server
```

### tcpdump - Capture réseau
```bash
# Capturer trafic sur interface
tcpdump -i eth0 port 6443

# Capturer et sauver
tcpdump -i any -w capture.pcap port 6443
```

### strace - Debug système
```bash
# Tracer les appels système
strace -p $(pidof kubelet)
strace kubectl get pods
```

### lsof - Fichiers ouverts
```bash
# Fichiers ouverts par kubelet
lsof -p $(pidof kubelet)

# Processus utilisant un port
lsof -i :6443
```

### Shortcuts shell utiles
```bash
# Alias pratiques à ajouter dans ~/.bashrc ou ~/.zshrc
alias k=kubectl
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deploy'
alias kgn='kubectl get nodes'
alias kdp='kubectl describe pod'
alias kl='kubectl logs'
alias klf='kubectl logs -f'
alias kex='kubectl exec -it'
alias kctx='kubectl config current-context'
alias kns='kubectl config set-context --current --namespace'

# Fonctions utiles
klog() { kubectl logs -f $(kubectl get pods | grep $1 | head -1 | awk '{print $1}') }
kexec() { kubectl exec -it $(kubectl get pods | grep $1 | head -1 | awk '{print $1}') -- /bin/bash }
```

## Debugging avancé

### Inspection complète d'un pod
```bash
# Tout en une commande
kubectl get pod mon-pod -o json | jq '{
  name: .metadata.name,
  namespace: .metadata.namespace,
  node: .spec.nodeName,
  phase: .status.phase,
  ip: .status.podIP,
  containers: [.spec.containers[] | {name: .name, image: .image, ready: .ready}],
  conditions: [.status.conditions[] | {type: .type, status: .status}]
}'
```

### Troubleshooting réseau
```bash
# Tester la connectivité depuis un pod
kubectl run test-pod --rm -it --image=nicolaka/netshoot -- /bin/bash
# Puis dans le pod:
# nslookup kubernetes.default
# curl -k https://kubernetes.default
# ping autre-service
```

### Analyse de performances
```bash
# Top ressources global
kubectl top nodes
kubectl top pods -A --sort-by=cpu
kubectl top pods -A --sort-by=memory

# Avec formatage
kubectl top pods -A --no-headers | sort -k3 -nr | head -10
```
