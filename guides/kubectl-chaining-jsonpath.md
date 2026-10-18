# Chaînage de commandes kubectl et JSONPath avancé

## Chaînage de commandes kubectl

### Méthode 1 : Substitution de commande (la plus simple)
```bash
# Avec $()
kubectl describe role -n kube-system $(kubectl get roles -n kube-system --no-headers | grep cert-manager-cainjector | awk '{print $1}')

# Version courte si vous connaissez le nom exact
kubectl describe role -n kube-system cert-manager-cainjector:leaderelection

# Avec backticks (ancienne syntaxe, moins recommandée)
kubectl describe role -n kube-system `kubectl get roles -n kube-system -o jsonpath='{.items[0].metadata.name}'`
```

### Méthode 2 : Variables shell
```bash
# Stocker dans une variable
ROLE_NAME=$(kubectl get roles -n kube-system --no-headers | grep cert-manager | head -1 | awk '{print $1}')
kubectl describe role -n kube-system $ROLE_NAME

# Ou en une ligne avec &&
ROLE=$(kubectl get roles -n kube-system -o jsonpath='{.items[0].metadata.name}') && kubectl describe role -n kube-system $ROLE
```

### Méthode 3 : xargs
```bash
# Avec xargs
kubectl get roles -n kube-system --no-headers | grep cert-manager | awk '{print $1}' | xargs -I {} kubectl describe role -n kube-system {}

# Version avec JSONPath
kubectl get roles -n kube-system -o jsonpath='{.items[0].metadata.name}' | xargs kubectl describe role -n kube-system

# Pour plusieurs ressources en parallèle
kubectl get roles -n kube-system --no-headers | awk '{print $1}' | xargs -P 5 -I {} kubectl describe role -n kube-system {}
```

### Méthode 4 : Fonctions shell réutilisables
```bash
# Ajouter dans ~/.bashrc ou ~/.zshrc
kdesc() {
    local resource=$1
    local name=$2
    local namespace=${3:-default}
    kubectl describe $resource -n $namespace $(kubectl get $resource -n $namespace --no-headers | grep $name | head -1 | awk '{print $1}')
}

# Usage:
kdesc role cert-manager kube-system

# Fonction pour get puis describe
kgd() {
    kubectl get $1 -n ${3:-default} $2 -o yaml | kubectl describe -f - -n ${3:-default}
}
```

### Méthode 5 : Boucles
```bash
# For loop pour plusieurs ressources
for role in $(kubectl get roles -n kube-system --no-headers | awk '{print $1}'); do
    echo "=== Role: $role ==="
    kubectl describe role -n kube-system $role
done

# Avec filtrage
for role in $(kubectl get roles -n kube-system -o jsonpath='{.items[*].metadata.name}'); do
    if [[ $role == *"cert-manager"* ]]; then
        kubectl describe role -n kube-system $role
    fi
done

# While read (meilleur pour gérer les espaces)
kubectl get roles -n kube-system --no-headers | while read name age; do
    echo "Describing role: $name"
    kubectl describe role -n kube-system $name
done
```

## JSONPath - Guide complet

### Syntaxe de base

```bash
# Structure générale
kubectl get <resource> -o jsonpath='{<expression>}'

# Élément simple
kubectl get pod mon-pod -o jsonpath='{.metadata.name}'
kubectl get pod mon-pod -o jsonpath='{.status.phase}'

# Éléments imbriqués
kubectl get pod mon-pod -o jsonpath='{.spec.containers[0].name}'
kubectl get pod mon-pod -o jsonpath='{.spec.containers[0].image}'

# Plusieurs valeurs
kubectl get pod mon-pod -o jsonpath='{.metadata.name}{"\t"}{.status.phase}{"\n"}'
```

### L'opérateur range

```bash
# Range sur un tableau (items)
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'

# Range avec plusieurs champs
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

# Range imbriqué (conteneurs dans pods)
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{" containers: "}{range .spec.containers[*]}{.name}{","}{end}{"\n"}{end}'

# Range avec conditions (limité)
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

# Sans range (si une seule ressource)
kubectl get pod mon-pod -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}'
```

### Syntaxe avancée

#### Indices de tableau
```bash
# Premier élément [0]
kubectl get pods -o jsonpath='{.items[0].metadata.name}'

# Dernier élément [-1] - NE FONCTIONNE PAS en JSONPath
# Utiliser: kubectl get pods -o json | jq '.items[-1].metadata.name'

# Plage [0:3] - NE FONCTIONNE PAS en JSONPath
# Utiliser: kubectl get pods -o json | jq '.items[0:3]'

# Tous les éléments [*]
kubectl get pods -o jsonpath='{.items[*].metadata.name}'

# Tous les conteneurs de tous les pods
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].name}'
```

#### Opérateurs et filtres

```bash
# JSONPath dans kubectl a des LIMITATIONS importantes :
# ❌ Pas de filtres conditionnels (== != < >)
# ❌ Pas de fonctions (length, min, max, etc.)
# ❌ Pas d'opérateurs logiques (and, or, not)
# ❌ Pas de regex

# Ce qui NE FONCTIONNE PAS en kubectl JSONPath :
kubectl get pods -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'  # ❌
kubectl get pods -o jsonpath='{.items[?(@.spec.containers[0].resources.limits)].metadata.name}'  # ❌

# SOLUTION : Utiliser jq pour les filtres
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'
kubectl get pods -o json | jq -r '.items[] | select(.spec.containers[0].resources.limits) | .metadata.name'
```

### Caractères spéciaux et échappement

```bash
# Tabulation
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

# Nouvelle ligne
kubectl get pods -o jsonpath='{.items[*].metadata.name}{"\n"}'

# Guillemets dans la sortie
kubectl get pods -o jsonpath='{range .items[*]}{"\""}{.metadata.name}{"\""}{"\n"}{end}'

# Espace
kubectl get pods -o jsonpath='{.items[*].metadata.name}{" "}'

# Accéder à des clés avec des caractères spéciaux
kubectl get pod mon-pod -o jsonpath='{.metadata.annotations.kubernetes\.io/created-by}'
kubectl get pod mon-pod -o jsonpath="{.metadata.annotations['app\.kubernetes\.io/name']}"

# Clés avec tirets ou points
kubectl get pod mon-pod -o jsonpath='{.metadata.labels.app\.kubernetes\.io/name}'
kubectl get pod mon-pod -o jsonpath='{.metadata.labels.app-name}'
```

### Formater la sortie

```bash
# Format tabulaire simple
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.podIP}{"\n"}{end}'

# Avec headers personnalisés
echo -e "NAME\tSTATUS\tIP" && kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.podIP}{"\n"}{end}'

# Utiliser column pour aligner
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{","}{.status.phase}{","}{.status.podIP}{"\n"}{end}' | column -t -s ','

# Format CSV
echo "name,namespace,status,ip" && kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{","}{.metadata.namespace}{","}{.status.phase}{","}{.status.podIP}{"\n"}{end}'

# Format JSON (reconstitué)
kubectl get pods -o jsonpath='{range .items[*]}{"{"}"name":"{.metadata.name}","status":"{.status.phase}"{"},"}{end}'
```

### Exemples pratiques par ressource

#### Pods
```bash
# Nom et node
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\n"}{end}'

# Nom, namespace, status, IP
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.podIP}{"\n"}{end}'

# Conteneurs et images
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{": "}{range .spec.containers[*]}{.name}={.image}{" "}{end}{"\n"}{end}'

# Resources requests
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].resources.requests.cpu}{"\t"}{.spec.containers[0].resources.requests.memory}{"\n"}{end}'

# Labels (tous)
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels}{"\n"}{end}'

# Label spécifique
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.app}{"\n"}{end}'

# Conditions
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{" conditions: "}{range .status.conditions[*]}{.type}={.status}{" "}{end}{"\n"}{end}'

# Volumes
kubectl get pod mon-pod -o jsonpath='{range .spec.volumes[*]}{.name}{"\t"}{.persistentVolumeClaim.claimName}{"\n"}{end}'

# Variables d'environnement
kubectl get pod mon-pod -o jsonpath='{range .spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
```

#### Nodes
```bash
# Nom et adresses IP
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.addresses[0].address}{"\n"}{end}'

# Capacités
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.capacity.cpu}{"\t"}{.status.capacity.memory}{"\n"}{end}'

# Taints
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.taints}{"\n"}{end}'

# Conditions
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" "}{range .status.conditions[*]}{.type}={.status}{" "}{end}{"\n"}{end}'

# Version kubelet
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kubeletVersion}{"\n"}{end}'

# OS
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.osImage}{"\n"}{end}'
```

#### Services
```bash
# Nom, type, ClusterIP
kubectl get svc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.type}{"\t"}{.spec.clusterIP}{"\n"}{end}'

# Avec ports
kubectl get svc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.ports[*]}{.port}:{.targetPort}/{.protocol}{" "}{end}{"\n"}{end}'

# External IPs (LoadBalancer)
kubectl get svc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.loadBalancer.ingress[0].ip}{"\n"}{end}'

# Selector
kubectl get svc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.selector}{"\n"}{end}'
```

#### Deployments
```bash
# Nom et replicas
kubectl get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.replicas}{"\t"}{.status.availableReplicas}{"\n"}{end}'

# Image
kubectl get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'

# Strategy
kubectl get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.strategy.type}{"\n"}{end}'
```

#### ConfigMaps et Secrets
```bash
# Clés dans un ConfigMap
kubectl get cm mon-configmap -o jsonpath='{.data}' | jq 'keys'
# Ou en JSONPath pur
kubectl get cm mon-configmap -o jsonpath='{range .data.*}{@}{"\n"}{end}'

# Valeur spécifique
kubectl get cm mon-configmap -o jsonpath='{.data.ma-clé}'

# Toutes les clés
kubectl get cm mon-configmap -o jsonpath='{range .data.*}{@}{"\n"}{end}'

# Secrets (encodés en base64)
kubectl get secret mon-secret -o jsonpath='{.data.password}' | base64 -d
```

#### PersistentVolumes et PVCs
```bash
# PV - Nom, capacité, status
kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.capacity.storage}{"\t"}{.status.phase}{"\n"}{end}'

# PVC - Nom, status, volume
kubectl get pvc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.spec.volumeName}{"\n"}{end}'
```

### Custom-columns (alternative à JSONPath)

```bash
# Syntaxe plus lisible que JSONPath
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP

# Avec ALL namespaces
kubectl get pods -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName

# Colonnes complexes
kubectl get pods -o custom-columns=NAME:.metadata.name,IMAGES:.spec.containers[*].image,RESTART:.status.containerStatuses[0].restartCount

# Avantages vs JSONPath :
# ✅ Headers automatiques
# ✅ Plus lisible
# ✅ Alignement automatique
# ❌ Mais moins flexible pour le formatage personnalisé
```

## Comparaison JSONPath vs jq vs custom-columns

### Quand utiliser chaque outil ?

#### JSONPath (kubectl natif)
```bash
# ✅ Bon pour :
# - Extractions simples
# - Une seule valeur ou liste simple
# - Pas besoin d'installation supplémentaire

# ❌ Limitations :
# - Pas de filtres conditionnels
# - Pas de calculs
# - Pas de transformations complexes
# - Formatage limité

# Exemple :
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
```

#### custom-columns (kubectl natif)
```bash
# ✅ Bon pour :
# - Affichage tabulaire
# - Plusieurs colonnes
# - Remplacer kubectl get avec colonnes par défaut

# ❌ Limitations :
# - Pas de filtres
# - Pas de calculs
# - Format fixe (tableau)

# Exemple :
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase
```

#### jq (externe, à installer)
```bash
# ✅ Excellent pour :
# - Filtres conditionnels complexes
# - Transformations de données
# - Calculs et agrégations
# - Format JSON en sortie
# - Requêtes complexes

# ❌ Nécessite :
# - Installation séparée
# - Syntaxe à apprendre

# Exemple :
kubectl get pods -o json | jq '.items[] | select(.status.phase=="Running") | {name: .metadata.name, ip: .status.podIP}'
```

### Exemples comparatifs

#### Tâche : Lister les pods Running uniquement

```bash
# Avec grep (simple mais fragile)
kubectl get pods | grep Running

# Avec jq (recommandé)
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'

# Avec field-selector (le meilleur pour ce cas)
kubectl get pods --field-selector=status.phase=Running
```

#### Tâche : Compter les pods par status

```bash
# Avec awk
kubectl get pods --no-headers | awk '{print $3}' | sort | uniq -c

# Avec jq (plus robuste)
kubectl get pods -o json | jq '.items | group_by(.status.phase) | map({status: .[0].status.phase, count: length})'

# Résultat jq formaté :
kubectl get pods -o json | jq -r '.items | group_by(.status.phase) | map({status: .[0].status.phase, count: length}) | .[] | "\(.status): \(.count)"'
```

#### Tâche : Extraire nom, namespace et node en CSV

```bash
# Avec JSONPath
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name},{.metadata.namespace},{.spec.nodeName}{"\n"}{end}'

# Avec custom-columns (plus lisible)
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NAMESPACE:.metadata.namespace,NODE:.spec.nodeName --no-headers | tr -s ' ' ','

# Avec jq (plus flexible)
kubectl get pods -A -o json | jq -r '.items[] | [.metadata.name, .metadata.namespace, .spec.nodeName] | @csv'
```

## Astuces et bonnes pratiques

### Debug JSONPath
```bash
# Voir la structure JSON complète
kubectl get pod mon-pod -o json | jq '.'

# Tester l'expression étape par étape
kubectl get pod mon-pod -o json | jq '.metadata'
kubectl get pod mon-pod -o json | jq '.metadata.name'

# Voir tous les chemins possibles
kubectl get pod mon-pod -o json | jq 'paths(scalars) | join(".")'

# Une fois le chemin trouvé, convertir en JSONPath
# jq : .metadata.name
# JSONPath : {.metadata.name}
```

### Gérer les valeurs manquantes
```bash
# Si un champ peut être absent, jq est plus robuste
# JSONPath affichera une erreur ou rien
kubectl get pods -o jsonpath='{.items[*].status.podIP}'

# jq peut gérer avec // (opérateur par défaut)
kubectl get pods -o json | jq -r '.items[] | .status.podIP // "N/A"'

# Ou select pour filtrer les null
kubectl get pods -o json | jq -r '.items[] | select(.status.podIP != null) | .status.podIP'
```

### Combiner avec d'autres outils
```bash
# JSONPath + column
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name},{.status.phase},{.status.podIP}{"\n"}{end}' | column -t -s ','

# JSONPath + grep
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\n"}{end}' | grep kube-system

# JSONPath + wc
kubectl get pods -o jsonpath='{.items[*].metadata.name}' | wc -w  # Compter les pods

# JSONPath + xargs
kubectl get pods -o jsonpath='{.items[*].metadata.name}' | xargs -n1 kubectl describe pod
```

### Performance
```bash
# Pour de gros clusters, limiter les champs récupérés
# ❌ Lent (récupère tout)
kubectl get pods -o json | jq '.items[].metadata.name'

# ✅ Plus rapide (seulement les champs nécessaires)
kubectl get pods -o jsonpath='{.items[*].metadata.name}'

# ✅ Encore plus rapide (colonnes custom)
kubectl get pods -o custom-columns=NAME:.metadata.name --no-headers

# ✅ Le plus rapide pour simplement les noms
kubectl get pods --no-headers -o name
```

## Fonctions shell avancées

### Fonction pour chaîner get et describe
```bash
# Ajouter à ~/.bashrc
kgetdesc() {
    local resource=$1
    local pattern=$2
    local namespace=${3:-default}

    local name=$(kubectl get $resource -n $namespace --no-headers | grep "$pattern" | head -1 | awk '{print $1}')

    if [ -z "$name" ]; then
        echo "No $resource found matching '$pattern' in namespace $namespace"
        return 1
    fi

    echo "Found: $name"
    kubectl describe $resource -n $namespace $name
}

# Usage:
# kgetdesc role cert-manager kube-system
# kgetdesc pod nginx default
```

### Fonction pour JSONPath interactif
```bash
kjsonpath() {
    local resource=$1
    local path=$2
    local namespace=${3:+"-n $3"}

    kubectl get $resource $namespace -o jsonpath="{$path}"
    echo  # Nouvelle ligne
}

# Usage:
# kjsonpath pods '.items[*].metadata.name'
# kjsonpath pod mon-pod '.status.phase' mon-namespace
```

### Fonction pour explorer la structure
```bash
kstruct() {
    local resource=$1
    local name=${2:+"$2"}
    local namespace=${3:+"-n $3"}

    if [ -z "$name" ]; then
        kubectl get $resource $namespace -o json | jq 'if type == "object" and has("items") then .items[0] else . end | paths(scalars) | join(".")' | sort | uniq
    else
        kubectl get $resource $name $namespace -o json | jq 'paths(scalars) | join(".")' | sort | uniq
    fi
}

# Usage:
# kstruct pods                    # Structure du premier pod
# kstruct pod mon-pod             # Structure d'un pod spécifique
# kstruct pod mon-pod mon-ns      # Avec namespace
```

## Visualiser et comprendre la structure JSON/YAML

### Méthode 1 : kubectl explain (documentation intégrée)

```bash
# Explication de base d'une ressource
kubectl explain pod
kubectl explain deployment
kubectl explain service

# Navigation dans la hiérarchie
kubectl explain pod.spec
kubectl explain pod.spec.containers
kubectl explain pod.spec.containers.resources
kubectl explain pod.status

# Afficher TOUS les champs (récursif)
kubectl explain pod --recursive

# Avec plus de détails
kubectl explain pod.spec.containers --recursive

# Format spécifique
kubectl explain pod.spec.containers.resources.limits

# Chercher un champ spécifique dans la doc
kubectl explain pod --recursive | grep -i "imagePullPolicy"

# Voir les types et descriptions
kubectl explain deployment.spec.strategy
kubectl explain deployment.spec.strategy.rollingUpdate

# Liste complète des ressources expliquées
kubectl api-resources --verbs=list -o name | xargs -I {} kubectl explain {}

# Exemples pratiques
kubectl explain pod.spec.containers.livenessProbe
kubectl explain pod.spec.volumes.persistentVolumeClaim
kubectl explain service.spec.ports
kubectl explain deployment.spec.template.spec.affinity
kubectl explain networkpolicy.spec
```

### Méthode 2 : Structure JSON avec jq (colorée et indentée)

```bash
# Basique - structure complète
kubectl get pod mon-pod -o json | jq '.'

# Avec less pour navigation (avec couleurs)
kubectl get pod mon-pod -o json | jq '.' | less -R

# Compacte
kubectl get pod mon-pod -o json | jq -c '.'

# Seulement certains niveaux de profondeur
kubectl get pod mon-pod -o json | jq 'del(.metadata.managedFields)'  # Enlever les champs verbeux

# Structure avec types
kubectl get pod mon-pod -o json | jq 'walk(if type == "object" then with_entries(.value = (.value | type)) else . end)'

# Voir uniquement les clés (arbre)
kubectl get pod mon-pod -o json | jq 'keys'
kubectl get pod mon-pod -o json | jq '.metadata | keys'
kubectl get pod mon-pod -o json | jq '.spec | keys'
kubectl get pod mon-pod -o json | jq '.status | keys'

# Afficher tous les chemins possibles (très utile!)
kubectl get pod mon-pod -o json | jq '[paths(scalars)] | map(join(".")) | .[]'

# Ou avec une meilleure présentation
kubectl get pod mon-pod -o json | jq -r 'paths(scalars) as $path | "\($path | join("."))"' | sort

# Structure en arbre avec valeurs
kubectl get pod mon-pod -o json | jq -C '.' | less -R

# Seulement certaines sections
kubectl get pod mon-pod -o json | jq '{metadata: .metadata, spec: .spec | keys, status: .status | keys}'
```

### Méthode 3 : yq pour YAML plus lisible

```bash
# YAML est souvent plus lisible que JSON
kubectl get pod mon-pod -o yaml

# Avec couleurs (si yq supporte)
kubectl get pod mon-pod -o yaml | yq e '.' - | less -R

# Simplifier en retirant les champs gérés
kubectl get pod mon-pod -o yaml | yq e 'del(.metadata.managedFields)' -

# Voir seulement la structure (clés)
kubectl get pod mon-pod -o yaml | yq e 'keys' -
kubectl get pod mon-pod -o yaml | yq e '.spec | keys' -

# Convertir en JSON pour jq
kubectl get pod mon-pod -o yaml | yq e -o=json '.' - | jq '.'

# Pretty print avec commentaires (pour apprentissage)
kubectl get pod mon-pod -o yaml | yq e '... comments=""' -
```

### Méthode 4 : Structure interactive avec fx

```bash
# Installer fx (terminal JSON viewer interactif)
npm install -g fx
# ou
sudo snap install fx

# Usage
kubectl get pod mon-pod -o json | fx

# Navigation:
# - Flèches haut/bas : naviguer
# - Entrée : développer/réduire
# - . : écrire du code jq
# - / : chercher
# - q : quitter

# Avec plusieurs ressources
kubectl get pods -o json | fx
```

### Méthode 5 : jq avec formatage personnalisé

```bash
# Arbre hiérarchique
kubectl get pod mon-pod -o json | jq -r '
  def tree(prefix):
    if type == "object" then
      to_entries[] | prefix + .key + ": " + (.value | type) + "\n" + (.value | tree(prefix + "  "))
    elif type == "array" then
      "[\(.length) items]"
    else
      ""
    end;
  tree("")'

# Résumé des sections principales
kubectl get pod mon-pod -o json | jq '{
  metadata: {
    name: .metadata.name,
    namespace: .metadata.namespace,
    labels: .metadata.labels | keys,
    annotations: .metadata.annotations | keys
  },
  spec: .spec | keys,
  status: .status | keys
}'

# Compter les champs à chaque niveau
kubectl get pod mon-pod -o json | jq '{
  metadata_fields: (.metadata | length),
  spec_fields: (.spec | length),
  status_fields: (.status | length),
  total_containers: (.spec.containers | length)
}'

# Lister tous les tableaux dans la structure
kubectl get pod mon-pod -o json | jq 'paths(type == "array") as $p | "\($p | join("."))"'

# Afficher la structure avec les types
kubectl get pod mon-pod -o json | jq '
  def show_types:
    if type == "object" then
      to_entries | map({(.key): (.value | type)}) | add
    else
      type
    end;
  show_types'
```

### Méthode 6 : bat pour coloration syntaxique améliorée

```bash
# Installer bat
sudo apt install bat  # Ou: cargo install bat

# Sur certains systèmes, bat s'appelle batcat
alias bat='batcat'

# Usage avec kubectl
kubectl get pod mon-pod -o json | bat -l json
kubectl get pod mon-pod -o yaml | bat -l yaml

# Avec pagination automatique
kubectl get pod mon-pod -o json | bat -l json --paging=always

# Avec numéros de ligne
kubectl get pod mon-pod -o yaml | bat -l yaml -n

# Style personnalisé
kubectl get pod mon-pod -o json | bat -l json --theme="Monokai Extended"
```

### Méthode 7 : Combinaisons pour exploration rapide

```bash
# Fonction complète d'exploration
kexplore() {
    local resource=$1
    local name=$2
    local namespace=${3:+-n $3}

    echo "=== Structure avec kubectl explain ==="
    kubectl explain $resource --recursive | head -50
    echo ""
    echo "=== Chemins JSON disponibles ==="
    kubectl get $resource $name $namespace -o json | jq -r 'paths(scalars) | join(".")' | head -30
    echo ""
    echo "=== Sections principales ==="
    kubectl get $resource $name $namespace -o json | jq '{metadata: (.metadata | keys), spec: (.spec | keys), status: (.status | keys)}'
}

# Usage: kexplore pod mon-pod default

# Fonction pour comparer structure vs données réelles
kcompare() {
    local resource=$1
    local name=$2
    local namespace=${3:+-n $3}

    echo "=== Documentation (explain) ==="
    kubectl explain $resource.spec | head -20
    echo ""
    echo "=== Données réelles ==="
    kubectl get $resource $name $namespace -o jsonpath='{.spec}' | jq '.'
}
```

### Méthode 8 : Scripts utilitaires

#### Script pour générer un template vide
```bash
#!/bin/bash
# save as: k-template.sh

RESOURCE=$1

kubectl explain $RESOURCE --recursive | awk '
BEGIN { print "apiVersion: v1"; print "kind: '$RESOURCE'" }
/^   [a-z]/ {
    indent = match($0, /[^ ]/)
    field = $1
    gsub(/[<>]/, "", $2)
    type = $2
    if (type == "string") print substr("                    ", 1, indent-3) field ": \"\""
    else if (type == "integer") print substr("                    ", 1, indent-3) field ": 0"
    else if (type == "boolean") print substr("                    ", 1, indent-3) field ": false"
}'

# Usage: ./k-template.sh Pod > pod-template.yaml
```

#### Script pour afficher la structure en arbre
```bash
#!/bin/bash
# save as: k-tree.sh

RESOURCE=$1
NAME=$2
NAMESPACE=${3:-default}

kubectl get $RESOURCE $NAME -n $NAMESPACE -o json | jq -r '
  def tree($prefix):
    if type == "object" then
      to_entries | .[] |
        "\($prefix)├── \(.key) (\(.value | type))" ,
        (.value | tree($prefix + "│   "))
    elif type == "array" then
      "[\(length) items]"
    else
      empty
    end;
  tree("")
'

# Usage: ./k-tree.sh pod mon-pod default
```

### Méthode 9 : Comparaison explicate vs réalité

```bash
# Voir ce qui est documenté
kubectl explain pod.spec.containers.resources

# Voir ce qui est configuré réellement
kubectl get pod mon-pod -o json | jq '.spec.containers[0].resources'

# Comparer les champs disponibles vs utilisés
comm -3 \
  <(kubectl explain pod.spec.containers --recursive | grep -o '^   [a-z][a-zA-Z]*' | sort | uniq) \
  <(kubectl get pod mon-pod -o json | jq -r '.spec.containers[0] | keys[]' | sort)

# Champs définis (à gauche seulement)
# Champs non utilisés (à droite seulement)
```

### Méthode 10 : Chercher un champ spécifique

```bash
# Trouver où est un champ dans explain
kubectl explain pod --recursive | grep -i "image" -B 2 -A 2

# Trouver le chemin complet d'un champ
kubectl get pod mon-pod -o json | jq -r 'paths(scalars) | join(".")' | grep -i image

# Trouver la valeur d'un champ quand on ne connaît pas le chemin exact
kubectl get pod mon-pod -o json | jq '.. | .image? // empty'

# Chercher tous les champs contenant "resource"
kubectl explain pod --recursive | grep -i resource

# Puis obtenir le détail
kubectl explain pod.spec.containers.resources
kubectl explain pod.spec.containers.resources.limits
kubectl explain pod.spec.containers.resources.requests
```

## Astuces pour débutants

### Workflow recommandé pour découvrir une ressource

1. **Commencer par explain**
```bash
kubectl explain deployment
```

2. **Explorer les sous-sections**
```bash
kubectl explain deployment.spec
kubectl explain deployment.spec.template
```

3. **Voir tout récursivement**
```bash
kubectl explain deployment --recursive | less
```

4. **Créer une ressource exemple**
```bash
kubectl create deployment test --image=nginx --dry-run=client -o yaml
```

5. **Examiner une vraie ressource**
```bash
kubectl get deployment test -o yaml
```

6. **Explorer avec jq**
```bash
kubectl get deployment test -o json | jq 'keys'
kubectl get deployment test -o json | jq '.spec | keys'
```

7. **Trouver les chemins pour JSONPath**
```bash
kubectl get deployment test -o json | jq -r 'paths(scalars) | join(".")'
```

### Ressources externes utiles

```bash
# API reference officielle (online)
# https://kubernetes.io/docs/reference/kubernetes-api/

# JSONPath online tester
# https://jsonpath.com/

# JSONPath kubectl simulator
# https://jsonpath.curlybraces.dev/

# Kubernetes examples
# https://github.com/kubernetes/examples
```

### Aide-mémoire quick reference

```bash
# Voir toute la structure d'une ressource
kubectl get <resource> <name> -o yaml | bat -l yaml

# Trouver un champ
kubectl explain <resource> --recursive | grep <champ>

# Voir les chemins JSONPath
kubectl get <resource> <name> -o json | jq -r 'paths(scalars) | join(".")'

# Tester un JSONPath
kubectl get <resource> <name> -o jsonpath='{.chemin.vers.champ}'

# Filtrer avec jq (plus puissant)
kubectl get <resource> -o json | jq '.items[] | select(.spec.field == "value")'

# Docs officielle d'un champ
kubectl explain <resource>.spec.champ
```
