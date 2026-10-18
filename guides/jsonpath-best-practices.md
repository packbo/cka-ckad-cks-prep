# JSONPath et JQ - Best Practices et Pièges à éviter

## ⚠️ ERREUR COURANTE : .items n'existe PAS toujours !

### La différence fondamentale

```bash
# ❌ LISTE (plusieurs ressources) → Contient .items
kubectl get pods                    # Liste de TOUS les pods
kubectl get pods -n mon-ns          # Liste des pods du namespace
kubectl get pods -A                 # Liste de TOUS les pods de TOUS les namespaces

# ✅ RESSOURCE UNIQUE → PAS de .items
kubectl get pod mon-pod            # UN SEUL pod spécifique
kubectl get pod mon-pod -n mon-ns  # UN pod spécifique dans un namespace
```

### Structure JSON réelle

#### Quand vous faites `kubectl get pods` (LISTE)
```json
{
  "apiVersion": "v1",
  "kind": "List",
  "items": [
    {
      "kind": "Pod",
      "metadata": {
        "name": "pod-1"
      },
      "spec": {...},
      "status": {...}
    },
    {
      "kind": "Pod",
      "metadata": {
        "name": "pod-2"
      },
      "spec": {...},
      "status": {...}
    }
  ]
}
```

**JSONPath pour une liste :**
```bash
# ✅ CORRECT - avec .items
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'

# ❌ FAUX - pas de .items
kubectl get pods -o jsonpath='{.metadata.name}'  # Retourne RIEN
```

#### Quand vous faites `kubectl get pod mon-pod` (RESSOURCE UNIQUE)
```json
{
  "apiVersion": "v1",
  "kind": "Pod",
  "metadata": {
    "name": "mon-pod",
    "namespace": "default"
  },
  "spec": {...},
  "status": {...}
}
```

**JSONPath pour une ressource unique :**
```bash
# ✅ CORRECT - PAS de .items
kubectl get pod mon-pod -o jsonpath='{.metadata.name}'
kubectl get pod mon-pod -o jsonpath='{.status.phase}'

# ❌ FAUX - il n'y a pas de .items
kubectl get pod mon-pod -o jsonpath='{.items[0].metadata.name}'  # Retourne RIEN
kubectl get pod mon-pod -o jsonpath='{range .items[*]}{.metadata.name}{end}'  # Retourne RIEN
```

## 🎯 Best Practices - Méthodes les plus simples

### Règle #1 : Vérifier d'abord la structure

```bash
# Méthode la plus simple pour comprendre ce que vous avez
kubectl get pods -o json | jq 'keys'
# Résultat: ["apiVersion", "items", "kind", "metadata"]
# → Vous voyez "items" ? C'est une liste !

kubectl get pod mon-pod -o json | jq 'keys'
# Résultat: ["apiVersion", "kind", "metadata", "spec", "status"]
# → Pas de "items" ? C'est une ressource unique !
```

### Règle #2 : Utiliser jq pour les listes (plus simple que JSONPath)

#### ❌ COMPLIQUÉ (JSONPath avec range)
```bash
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

#### ✅ SIMPLE (jq)
```bash
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name)\t\(.status.phase)"'
```

#### ✅ ENCORE PLUS SIMPLE (jq avec @tsv)
```bash
kubectl get pods -o json | jq -r '.items[] | [.metadata.name, .status.phase] | @tsv'
```

### Règle #3 : JSONPath pour extractions simples seulement

```bash
# ✅ BON USAGE de JSONPath (simple, une seule valeur)
kubectl get pod mon-pod -o jsonpath='{.status.podIP}'
kubectl get pod mon-pod -o jsonpath='{.spec.nodeName}'
kubectl get pod mon-pod -o jsonpath='{.metadata.namespace}'

# ✅ BON USAGE (liste simple)
kubectl get pods -o jsonpath='{.items[*].metadata.name}'

# ❌ TROP COMPLIQUÉ pour JSONPath → Utiliser jq
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.spec.nodeName}{"\n"}{end}'
```

### Règle #4 : jq pour filtres et conditions

```bash
# ❌ IMPOSSIBLE avec JSONPath
kubectl get pods -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'

# ✅ FACILE avec jq
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'

# ✅ Filtres multiples
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running" and .metadata.namespace!="kube-system") | .metadata.name'
```

## 📋 Tableau de décision : Quel outil utiliser ?

| Besoin | Outil recommandé | Exemple |
|--------|------------------|---------|
| Une seule valeur simple | `jsonpath` | `kubectl get pod mon-pod -o jsonpath='{.status.phase}'` |
| Liste de valeurs simples | `jsonpath` | `kubectl get pods -o jsonpath='{.items[*].metadata.name}'` |
| Formatage tabulaire | `custom-columns` | `kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase` |
| Filtrer par condition | `jq` | `kubectl get pods -o json \| jq '.items[] \| select(.status.phase=="Running")'` |
| Transformer la structure | `jq` | `kubectl get pods -o json \| jq '{name: .items[].metadata.name}'` |
| Calculs/comptage | `jq` | `kubectl get pods -o json \| jq '.items \| length'` |
| Multiple champs avec formatage | `jq` | `kubectl get pods -o json \| jq -r '.items[] \| [.metadata.name, .status.phase] \| @tsv'` |

## 🔍 Exemples comparatifs : Liste vs Ressource unique

### Exemple 1 : Obtenir le nom

```bash
# LISTE (plusieurs pods)
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
kubectl get pods -o json | jq -r '.items[].metadata.name'

# RESSOURCE UNIQUE (un seul pod)
kubectl get pod mon-pod -o jsonpath='{.metadata.name}'
kubectl get pod mon-pod -o json | jq -r '.metadata.name'
```

### Exemple 2 : Obtenir plusieurs champs

```bash
# LISTE
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name) \(.status.phase) \(.status.podIP)"'

# RESSOURCE UNIQUE
kubectl get pod mon-pod -o json | jq -r '"\(.metadata.name) \(.status.phase) \(.status.podIP)"'
```

### Exemple 3 : Conteneurs et images

```bash
# LISTE (tous les pods)
kubectl get pods -o json | jq -r '.items[] | .metadata.name as $pod | .spec.containers[] | "\($pod): \(.name)=\(.image)"'

# RESSOURCE UNIQUE (un pod)
kubectl get pod mon-pod -o json | jq -r '.spec.containers[] | "\(.name)=\(.image)"'
```

## 🚀 Patterns les plus utilisés (copier-coller)

### Pattern 1 : Lister tous les noms (liste)
```bash
# Simple
kubectl get pods -o jsonpath='{.items[*].metadata.name}'

# Avec nouvelle ligne (jq)
kubectl get pods -o json | jq -r '.items[].metadata.name'

# Séparés par virgule
kubectl get pods -o json | jq -r '.items[].metadata.name' | paste -sd ','
```

### Pattern 2 : Nom + Status + IP (liste)
```bash
# Avec jq (recommandé)
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name)\t\(.status.phase)\t\(.status.podIP)"'

# Avec custom-columns (simple aussi)
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP
```

### Pattern 3 : Filtrer par status
```bash
# Pods Running seulement
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'

# Pods NOT Running
kubectl get pods -o json | jq -r '.items[] | select(.status.phase!="Running") | .metadata.name'

# Avec field-selector (encore plus simple pour ce cas!)
kubectl get pods --field-selector=status.phase=Running
```

### Pattern 4 : Compter
```bash
# Nombre total de pods
kubectl get pods -o json | jq '.items | length'

# Nombre de pods Running
kubectl get pods -o json | jq '[.items[] | select(.status.phase=="Running")] | length'

# Par status
kubectl get pods -o json | jq '.items | group_by(.status.phase) | map({status: .[0].status.phase, count: length})'
```

### Pattern 5 : Conteneurs et images
```bash
# Liste (tous les pods)
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name): \(.spec.containers[].image)"'

# Unique (un pod)
kubectl get pod mon-pod -o json | jq -r '.spec.containers[] | "\(.name): \(.image)"'

# Toutes les images uniques utilisées
kubectl get pods -A -o json | jq -r '.items[].spec.containers[].image' | sort -u
```

### Pattern 6 : Resources (requests/limits)
```bash
# Liste
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name) CPU:\(.spec.containers[0].resources.requests.cpu // "N/A") MEM:\(.spec.containers[0].resources.requests.memory // "N/A")"'

# Unique
kubectl get pod mon-pod -o json | jq '.spec.containers[0].resources'
```

### Pattern 7 : Labels
```bash
# Liste - tous les labels
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name): \(.metadata.labels)"'

# Un label spécifique
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name): \(.metadata.labels.app // "N/A")"'

# Filtrer par label (utiliser -l à la place!)
kubectl get pods -l app=nginx  # ✅ Plus simple !
kubectl get pods -o json | jq -r '.items[] | select(.metadata.labels.app=="nginx") | .metadata.name'
```

### Pattern 8 : Node assignment
```bash
# Liste
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name)\t\(.spec.nodeName // "N/A")"'

# Grouper par node
kubectl get pods -o json | jq -r '.items | group_by(.spec.nodeName) | map({node: .[0].spec.nodeName, pods: length})'
```

## 🎓 Workflow simplifié pour débutants

### Étape 1 : Toujours commencer par voir la structure
```bash
kubectl get pods -o json | jq 'keys'
# ou
kubectl get pod mon-pod -o json | jq 'keys'
```

### Étape 2 : Explorer les sections
```bash
kubectl get pod mon-pod -o json | jq '.metadata | keys'
kubectl get pod mon-pod -o json | jq '.spec | keys'
kubectl get pod mon-pod -o json | jq '.status | keys'
```

### Étape 3 : Tester l'extraction
```bash
# Essayer d'abord dans jq
kubectl get pod mon-pod -o json | jq '.metadata.name'

# Si ça marche et c'est simple, convertir en JSONPath
kubectl get pod mon-pod -o jsonpath='{.metadata.name}'
```

### Étape 4 : Si c'est complexe, rester avec jq
```bash
# Filtres, conditions, transformations → jq
kubectl get pods -o json | jq '.items[] | select(.status.phase=="Running")'
```

## ⚡ Erreurs courantes et corrections

### Erreur 1 : Confondre liste et ressource unique
```bash
# ❌ FAUX
kubectl get pod mon-pod -o jsonpath='{.items[0].metadata.name}'

# ✅ CORRECT
kubectl get pod mon-pod -o jsonpath='{.metadata.name}'
```

### Erreur 2 : Oublier .items dans une liste
```bash
# ❌ FAUX
kubectl get pods -o jsonpath='{.metadata.name}'

# ✅ CORRECT
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
```

### Erreur 3 : JSONPath trop complexe
```bash
# ❌ COMPLIQUÉ ET FRAGILE
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.podIP}{"\t"}{.spec.nodeName}{"\n"}{end}'

# ✅ SIMPLE ET LISIBLE
kubectl get pods -o json | jq -r '.items[] | [.metadata.name, .status.phase, .status.podIP, .spec.nodeName] | @tsv'

# ✅✅ ENCORE MIEUX (natif kubectl)
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP,NODE:.spec.nodeName
```

### Erreur 4 : Essayer de filtrer avec JSONPath
```bash
# ❌ NE FONCTIONNE PAS (JSONPath kubectl ne supporte pas les filtres)
kubectl get pods -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'

# ✅ CORRECT avec jq
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'

# ✅✅ ENCORE MIEUX (field-selector natif)
kubectl get pods --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}'
```

### Erreur 5 : Ne pas gérer les valeurs manquantes
```bash
# ❌ Peut retourner "null" ou erreur
kubectl get pods -o json | jq -r '.items[].status.podIP'

# ✅ CORRECT avec valeur par défaut
kubectl get pods -o json | jq -r '.items[] | .status.podIP // "N/A"'

# ✅ Ou filtrer les nulls
kubectl get pods -o json | jq -r '.items[] | select(.status.podIP != null) | .status.podIP'
```

## 🔧 Outils natifs kubectl à privilégier

### Avant de se lancer dans JSONPath/jq, vérifier ces options natives :

```bash
# 1. Field selectors (filtrer par champ)
kubectl get pods --field-selector=status.phase=Running
kubectl get pods --field-selector=metadata.namespace=default
kubectl get events --field-selector involvedObject.kind=Pod

# 2. Label selectors (filtrer par label)
kubectl get pods -l app=nginx
kubectl get pods -l 'app in (nginx,apache)'
kubectl get pods -l app!=nginx

# 3. Custom columns (formatage tabulaire)
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName

# 4. Output formats simples
kubectl get pods -o name              # Juste les noms (avec type)
kubectl get pods -o wide              # Plus d'info
kubectl get pods -o yaml              # YAML complet
kubectl get pods -o json              # JSON complet

# 5. Sort-by (trier)
kubectl get pods --sort-by=.metadata.creationTimestamp
kubectl get pods --sort-by=.status.podIP

# 6. Show labels
kubectl get pods --show-labels
```

## 📝 Cheatsheet final : Quand utiliser quoi ?

```bash
# Besoin : Lister les noms seulement
kubectl get pods -o name                                    # ✅ Le plus simple

# Besoin : Filtrer par label
kubectl get pods -l app=nginx                               # ✅ Le plus simple

# Besoin : Filtrer par status
kubectl get pods --field-selector=status.phase=Running      # ✅ Le plus simple

# Besoin : Plusieurs colonnes personnalisées
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase  # ✅ Le plus simple

# Besoin : Une seule valeur d'une ressource
kubectl get pod mon-pod -o jsonpath='{.status.phase}'       # ✅ Simple et efficace

# Besoin : Filtrer avec conditions complexes
kubectl get pods -o json | jq '.items[] | select(...)'      # ✅ jq obligatoire

# Besoin : Transformer la structure JSON
kubectl get pods -o json | jq '{name: .items[].metadata.name, ...}'  # ✅ jq obligatoire

# Besoin : Calculs, agrégations, group by
kubectl get pods -o json | jq '...'                         # ✅ jq obligatoire
```

## 💡 Résumé des Best Practices

1. **Toujours vérifier si c'est une liste ou une ressource unique**
   - Liste → `.items[]` ou `.items[*]`
   - Unique → Pas de `.items`

2. **Privilégier les outils natifs kubectl d'abord**
   - `--field-selector`, `-l`, `--sort-by`, `-o custom-columns`

3. **JSONPath pour extractions simples seulement**
   - Une valeur, ou liste simple de valeurs

4. **jq pour tout ce qui est complexe**
   - Filtres, conditions, transformations, calculs

5. **custom-columns pour les tableaux formatés**
   - Alternative lisible à JSONPath avec range

6. **Toujours tester avec `| jq 'keys'` pour voir la structure**
   - Évite les erreurs de chemin

7. **Utiliser `// "N/A"` dans jq pour gérer les valeurs manquantes**
   - Évite les "null" dans la sortie
