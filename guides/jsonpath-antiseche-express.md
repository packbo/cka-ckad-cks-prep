# Anti-sèche Express JSONPath / jq / kubectl (Mode Examen CKA)

> Version **condensée** pensée pour le jour J. Tout sur une page, ordre de frappe
> rapide. À garder ouverte dans un onglet pendant la pratique.

---

## Setup obligatoire (2 min, début d'examen)

```bash
alias k=kubectl
complete -F __start_kubectl k
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"
echo 'set ts=2 sw=2 et' >> ~/.vimrc
```

---

## Réflexe n°1 : trouver un chemin (NE JAMAIS DEVINER)

```bash
# Tous les chemins disponibles d'une ressource :
kubectl get pod X -o json | jq -r 'paths(scalars)|join(".")'

# Chercher un champ précis (ex : image, ip, node, cpu) :
kubectl get pod X -o json | jq -r 'paths(scalars)|join(".")' | grep -i image

# Trouver une valeur sans connaître le chemin :
kubectl get pod X -o json | jq '.. | .image? // empty'
```

---

## Réflexe n°2 : liste vs ressource unique (LE piège #1)

```bash
# LISTE  (kubectl get pods)       →  il FAUT .items[*]
kubectl get pods  -o jsonpath='{.items[*].metadata.name}'

# UNIQUE (kubectl get pod X)      →  PAS de .items
kubectl get pod X -o jsonpath='{.metadata.name}'
```

**Vérification rapide :** `kubectl get pod X -o json | jq 'keys'`
→ si tu vois `"items"` c'est une liste.

---

## Tableau de décision immédiat

| Je veux… | Commande (la + simple) |
|----------|------------------------|
| Les noms | `k get pods -o name` |
| Filtrer par label | `k get pods -l app=nginx` |
| Filtrer par status | `k get pods --field-selector=status.phase=Running` |
| Trier | `k get pods --sort-by=.metadata.creationTimestamp` |
| Voir les labels | `k get pods --show-labels` |
| Un tableau lisible | `k get pods -o custom-columns=NAME:.metadata.name,IMG:.spec.containers[0].image` |
| UNE valeur d'un objet | `k get pod X -o jsonpath='{.status.phase}'` |
| Filtrer avec condition | `k get pods -o json \| jq -r '.items[] \| select(.status.phase=="Running") \| .metadata.name'` |
| Compter | `k get pods -o json \| jq '.items \| length'` |

---

## Patterns prêts à copier (les + fréquents au CKA)

```bash
# Image du 1er container d'un pod
k get pod X -o jsonpath='{.spec.containers[0].image}'

# Toutes les images de tous les pods (tous namespaces)
k get pods -A -o jsonpath='{.items[*].spec.containers[*].image}'

# Nom + image (tableau propre)
k get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image

# Node de chaque pod
k get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName

# Nom + IP + status
k get pods -o custom-columns=NAME:.metadata.name,IP:.status.podIP,STATUS:.status.phase

# Pods Running uniquement
k get pods --field-selector=status.phase=Running

# Taints d'un node
k get node X -o jsonpath='{.spec.taints}'

# IP cluster d'un service
k get svc X -o jsonpath='{.spec.clusterIP}'

# Endpoints d'un service (debug)
k get endpoints X

# Valeur base64 d'un secret (décodée)
k get secret X -o jsonpath='{.data.password}' | base64 -d

# Liste des namespaces
k get ns -o jsonpath='{.items[*].metadata.name}'
```

---

## Règle : quand utiliser quoi

```
SIMPLE (1 valeur ou 1 liste simple)   →  -o jsonpath='{...}'
TABLEAU FORMATÉ                        →  -o custom-columns=...
FILTRER / CONDITIONS / CALCULS         →  -o json | jq ...
JUSTE LES NOMS                         →  -o name
FILTRER PAR CHAMP                      →  --field-selector=...
FILTRER PAR LABEL                      →  -l clé=valeur
```

> **Important :** JSONPath de kubectl **ne supporte PAS** les filtres
> (`?(@...=="...")` ne marche PAS). Pour filtrer → `jq` ou `--field-selector`.

---

## Pièges qui font perdre des points

| Piège | Correction |
|-------|------------|
| `kubectl get pod X -o jsonpath='{.items...}'` | UNIQUE → pas de `.items` |
| `kubectl get pods -o jsonpath='{.metadata.name}'` | LISTE → il faut `.items[*]` |
| Filtrer avec JSONPath `?(@...)` | Marche pas → `jq` ou `--field-selector` |
| Oublier le `-r` dans jq → guillemets | `jq -r '...'` pour texte brut |
| Valeur `null` affichée | `// "N/A"` dans jq |
| `[-1]` (dernier élément) en JSONPath | Marche pas → `jq '.[-1]'` |

---

## Vérifications de fin de question (TOUJOURS)

```bash
k get pods                     # la ressource existe ?
k describe pod X               # Events = pas d'erreur ?
k config current-context       # bon cluster ?
k config view --minify | grep namespace   # bon namespace ?
```
