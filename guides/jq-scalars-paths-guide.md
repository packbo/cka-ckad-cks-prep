# Guide jq, Paths et "Scalars" - Comprendre la structure JSON Kubernetes

> Ce guide explique en profondeur les notions de **scalars**, de **paths**, et comment
> utiliser `jq` pour explorer n'importe quelle ressource Kubernetes. C'est LA compétence
> clé pour réussir les questions CKA qui demandent d'extraire une valeur précise.

---

## 1. Qu'est-ce qu'un "scalar" ?

En JSON / jq, les valeurs se divisent en **2 grandes familles** :

### Les scalars (valeurs simples / atomiques)
Un *scalar* est une valeur **unique**, qui ne contient pas d'autres valeurs.

| Type scalar | Exemple | Description |
|-------------|---------|-------------|
| `string`    | `"nginx"` | Du texte |
| `number`    | `3`, `1.5`, `80` | Un nombre |
| `boolean`   | `true`, `false` | Vrai / faux |
| `null`      | `null` | Absence de valeur |

### Les non-scalars (collections / conteneurs)
Une valeur qui **contient** d'autres valeurs.

| Type non-scalar | Exemple | Description |
|-----------------|---------|-------------|
| `object`        | `{"name": "nginx"}` | Un dictionnaire (clé → valeur) |
| `array`         | `["a", "b", "c"]` | Une liste ordonnée |

### Pourquoi c'est important ?
Dans la structure JSON d'un Pod, la plupart des "chemins" mènent à un *container*
(object/array) et seulement **quelques-uns** mènent à une vraie valeur (scalar).
On veut généralement récupérer les scalars = les vraies données.

```
.metadata                 ← OBJECT (non-scalar, contient d'autres trucs)
.metadata.name            ← STRING "nginx"  (SCALAR ✓ la vraie donnée)
.metadata.namespace       ← STRING "default" (SCALAR ✓)
.spec                     ← OBJECT
.spec.containers          ← ARRAY [ ... ]    (non-scalar)
.spec.containers[0]       ← OBJECT
.spec.containers[0].image ← STRING "nginx:1.21" (SCALAR ✓ la vraie donnée)
```

---

## 2. La commande magique : `paths(scalars)`

`paths(scalars)` génère **toutes les adresses** qui mènent à une vraie valeur (un scalar).
C'est l'outil parfait pour découvrir le bon chemin JSONPath sans deviner.

### Utilisation de base

```bash
# Afficher TOUS les chemins possibles d'une ressource
kubectl get pod mon-pod -o json | jq -r 'paths(scalars) | join(".")'
```

Résultat type :
```
apiVersion
kind
metadata.name
metadata.namespace
metadata.uid
metadata.creationTimestamp
spec.containers[0].name
spec.containers[0].image
spec.containers[0].ports[0].containerPort
status.phase
status.podIP
status.startTime
...
```

### Trouver un champ précis (ex : "image")

```bash
# Je cherche où se trouve "image" dans la structure
kubectl get pod mon-pod -o json | jq -r 'paths(scalars) | join(".")' | grep -i image
# → spec.containers[0].image
```

→ Vous avez maintenant le chemin exact ! Convertissez-le en JSONPath :
```bash
kubectl get pod mon-pod -o jsonpath='{.spec.containers[0].image}'
```

### Trouver une VALEUR sans connaître le chemin

```bash
# Cherche n'importe où dans l'arbre un champ "image" et affiche sa valeur
kubectl get pod mon-pod -o json | jq '.. | .image? // empty'
```

`..` = cherche récursivement partout. Très utile quand la structure est inconnue.

---

## 3. Explorer la structure étape par étape

Ne plongez pas au hasard. Explorez niveau par niveau avec `keys`.

```bash
# Niveau racine
kubectl get pod mon-pod -o json | jq 'keys'
# → ["apiVersion", "kind", "metadata", "spec", "status"]

# Niveau metadata
kubectl get pod mon-pod -o json | jq '.metadata | keys'
# → ["annotations", "creationTimestamp", "labels", "name", "namespace", ...]

# Niveau spec
kubectl get pod mon-pod -o json | jq '.spec | keys'
# → ["containers", "dnsPolicy", "nodeName", "restartPolicy", "volumes", ...]

# Descendre dans containers (c'est un ARRAY → on prend [0])
kubectl get pod mon-pod -o json | jq '.spec.containers[0] | keys'
# → ["image", "name", "ports", "resources", ...]
```

### Mémo : `keys` vs chemins complets
| Besoin | Commande |
|--------|----------|
| Clés directes d'un niveau | `jq '.spec \| keys'` |
| Tous les chemins (adresses) | `jq -r 'paths(scalars) \| join(".")'` |
| Structure visuelle complète | `jq '.'` |

---

## 4. Convertir un chemin jq → JSONPath kubectl

Les deux syntaxes sont presque identiques, mais il faut **ajouter un `.` au début**
et **envelopper dans `{...}`**.

| En jq | En JSONPath kubectl |
|-------|---------------------|
| `.metadata.name` | `{.metadata.name}` |
| `.spec.containers[0].image` | `{.spec.containers[0].image}` |
| `.items[].metadata.name` (liste) | `{.items[*].metadata.name}` |

### Workflow recommandé (toujours le même !)

```bash
# 1. Tester d'abord avec jq (plus tolérant)
kubectl get pod mon-pod -o json | jq '.spec.containers[0].image'
# → "nginx:1.21"

# 2. Si ça marche → convertir en JSONPath
kubectl get pod mon-pod -o jsonpath='{.spec.containers[0].image}'
```

---

## 5. Pièges fréquents liés aux scalars / paths

### Piège 1 : Confondre objet et valeur
```bash
# ❌ Ça affiche tout l'objet (pas une valeur)
kubectl get pod mon-pod -o json | jq '.metadata.labels'
# → {"app":"nginx","tier":"web"}    ← c'est un OBJECT, pas un scalar

# ✅ Une seule valeur (scalar)
kubectl get pod mon-pod -o json | jq -r '.metadata.labels.app'
# → nginx
```

### Piège 2 : Valeur manquante → null
En JSONPath, un champ absent → sortie vide ou erreur. En jq, on obtient `null`.

```bash
# Si .status.podIP n'existe pas (pod pas encore démarré)
kubectl get pod mon-pod -o json | jq '.status.podIP'      # → null
kubectl get pod mon-pod -o json | jq -r '.status.podIP'   # → "null" ( texte)

# ✅ Gérer avec // (valeur par défaut)
kubectl get pod mon-pod -o json | jq -r '.status.podIP // "N/A"'
# → N/A
```

### Piège 3 : `paths(scalars)` saute les nulls… attention
`paths(scalars)` **n'affiche pas** les chemins qui mènent à `null`. Si un champ
est absent, il n'apparaîtra pas dans la liste. Ne paniquez pas — testez avec
`jq '.leChemin'` pour confirmer.

### Piège 4 : JSONPath n'ajoute PAS de saut de ligne final
C'est l'erreur la plus visible : le prompt revient collé à la valeur.
```
$ kubectl get pod dns-test -o jsonpath='{.spec.containers[0].image}'
busybox$ _       ← le prompt est collé, illisible !
```

```bash
# ❌ Pas de newline → résultat collé au prompt
kubectl get pod X -o jsonpath='{.spec.containers[0].image}'

# ✅ Solution 1 : ajouter {"\n"} DANS l'expression
kubectl get pod X -o jsonpath='{.spec.containers[0].image}{"\n"}'

# ✅ Solution 2 : echo après
kubectl get pod X -o jsonpath='{.spec.containers[0].image}'; echo

# ✅ Solution 3 : jq ajoute toujours un newline final
kubectl get pod X -o json | jq -r '.spec.containers[0].image'
```

> **Règle CKA :** ajoute systématiquement `{"\n"}` à la fin de tes JSONPath,
> ou utilise `jq -r` (gère le saut de ligne tout seul).

### Piège 5 : `[0]` vs `[*]` — choisir le bon selon le nombre d'éléments
L'indice dépend du nombre d'éléments dans le tableau (containers, pods, ports...).

```bash
# [0] = SEULEMENT le 1er container (quand le pod en a 1 seul)
kubectl get pod X -o jsonpath='{.spec.containers[0].image}{"\n"}'

# [*] = TOUS les containers (multi-container, ou "list ALL")
kubectl get pod X -o jsonpath='{.spec.containers[*].image}{"\n"}'
```

**Comment savoir combien il y en a ?**
```bash
# Compter les containers
kubectl get pod X -o json | jq '.spec.containers | length'
# → 1  → [0] suffit
# → 3  → utilise [*] + range
```

**Piège dans `[*]` sans `range` :** tout est collé sur une ligne.
```bash
# ❌ Illisible : nginxredisbusybox
kubectl get pod X -o jsonpath='{.spec.containers[*].image}'

# ✅ Avec range + nom pour distinguer chaque container
kubectl get pod X -o jsonpath='{range .spec.containers[*]}{.name}={.image}{"\n"}{end}'
# → main=nginx
#   sidecar=redis
```

> **Règle CKA :** si la question dit "list **all** containers/images" → `[*]` + `range`.
> Si elle dit "the image" (singulier) → `[0]` suffit.
> Pense aussi aux **initContainers** (chemin séparé : `.spec.initContainers[*]`).

---

## 6. Exemples pratiques CKA

### Exemple 1 : "Quelle image utilise le 1er container ?"
```bash
# Découverte
kubectl get pod web -o json | jq -r 'paths(scalars)|join(".")' | grep image
# → spec.containers[0].image

# Réponse
kubectl get pod web -o jsonpath='{.spec.containers[0].image}'
```

### Exemple 2 : "Lister toutes les images de tous les pods"
```bash
# Liste → .items[*] puis .spec.containers[*] (double tableau)
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'
```

### Exemple 3 : "Nom + image pour chaque pod" (format lisible)
```bash
# custom-columns = la méthode la plus simple au CKA
kubectl get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

### Exemple 4 : "Le pod tourne sur quel node ?"
```bash
kubectl get pod web -o json | jq -r 'paths(scalars)|join(".")' | grep -i node
# → spec.nodeName
kubectl get pod web -o jsonpath='{.spec.nodeName}'
```

### Exemple 5 : "Extraire le certificat d'un secret (base64)"
```bash
# Un secret stocke les valeurs en base64 dans .data (OBJECT de scalars)
kubectl get secret mon-secret -o json | jq -r '.data'           # tout l'objet
kubectl get secret mon-secret -o json | jq -r '.data.password'  # valeur base64
kubectl get secret mon-secret -o jsonpath='{.data.password}' | base64 -d  # décodé
```

---

## 7. Deployment, StatefulSet, DaemonSet, Job : le chemin change !

**Piège majeur :** pour les ressources qui créent des pods via un **template**,
l'image n'est **pas** à `.spec.containers` mais à `.spec.template.spec.containers`.

### La ressource elle-même (état désiré = le template)
```bash
# Deployment → chemin avec .spec.template
kubectl get deploy nginx -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

### Les pods réellement créés (état réel)
Un Deployment **ne contient pas** ses pods — ce sont des ressources séparées.
On les atteint via leur **label** :
```bash
# Voir les pods du deployment
kubectl get pods -l app=nginx

# Image de chaque pod réel (chemin "normal")
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

### Trouver le chemin toi-même
```bash
# Sur le deployment → tu verras .spec.template.spec...
kubectl get deploy nginx -o json | jq -r 'paths(scalars)|join(".")' | grep image

# Sur un pod du deployment → chemin "normal" .spec.containers...
kubectl get pods -l app=nginx -o json | jq -r 'paths(scalars)|join(".")' | grep image
```

### Tableau récapitulatif des chemins d'image
| Ressource | Chemin de l'image |
|-----------|-------------------|
| Pod | `.spec.containers[0].image` |
| Deployment | `.spec.template.spec.containers[0].image` |
| StatefulSet / DaemonSet | `.spec.template.spec.containers[0].image` |
| Job | `.spec.template.spec.containers[0].image` |
| CronJob | `.spec.jobTemplate.spec.template.spec.containers[0].image` |

> **Astuce mémoire :** tout ce qui crée des pods via un template
> (Deploy, STS, DS, Job) → `.spec.template.spec.containers...`.
> Seul le Pod direct a `.spec.containers...`.

> **Au CKA :** si une question parle d'un "Deployment", vérifie ce qu'elle demande —
> l'image *configurée* (→ sur le Deploy) ou l'image *qui tourne réellement*
> (→ sur ses Pods via `-l`).

---

## 8. `kubectl explain` : ta doc hors-ligne

`explain` est **complémentaire** de `paths(scalars)`. Ils ne servent pas le même
usage :

| Outil | Ce qu'il montre | Quand l'utiliser |
|-------|-----------------|------------------|
| `kubectl explain pod.spec --recursive` | Le **schéma** = TOUS les champs possibles (même vides) | Tu ignores si un champ existe / son nom exact |
| `paths(scalars)` sur ressource réelle | Les champs **réellement peuplés** + valeurs | Tu veux le chemin + la valeur exacte |

### Cas où `explain` est irremplaçable
```bash
# 1. Trouver un champ dont tu ignores le nom (chercher dans le schéma)
kubectl explain pod.spec --recursive | grep -i image
# → révèle que "image" vit sous spec.containers.image

# 2. Comprendre la structure avant d'écrire du YAML
kubectl explain pod.spec.containers.resources
kubectl explain deployment.spec.strategy.rollingUpdate

# 3. Voir TOUT l'arbre d'une ressource
kubectl explain pod --recursive | less
kubectl explain networkpolicy.spec --recursive
```

### Limite à connaître
`explain` montre le schéma officiel, mais **pas toujours** les champs ajoutés par
ton cluster (CRDs, versions d'API). Pour une ressource concrète, `paths(scalars)`
est plus fiable.

### Bon réflexe — combiner les deux
```bash
# 1. explain pour confirmer qu'un champ existe et son chemin
kubectl explain pod.spec.containers --recursive | grep -i image

# 2. paths(scalars) sur le pod réel pour la valeur exacte
kubectl get pod X -o json | jq -r 'paths(scalars)|join(".")' | grep image

# 3. Extraire
kubectl get pod X -o jsonpath='{.spec.containers[0].image}{"\n"}'
```

---

## 9. Anti-sèche récapitulative

```bash
# === DÉCOUVRIR ===
kubectl get pod X -o json | jq 'keys'                           # clés racine
kubectl get pod X -o json | jq '.spec | keys'                   # clés d'un niveau
kubectl get pod X -o json | jq -r 'paths(scalars)|join(".")'    # tous les chemins
kubectl get pod X -o json | jq '.. | .image? // empty'          # valeur inconnue

# === EXTRAIRE (après avoir trouvé le chemin) ===
kubectl get pod X -o jsonpath='{.spec.containers[0].image}'     # 1 valeur
kubectl get pods  -o jsonpath='{.items[*].metadata.name}'       # 1 liste simple
kubectl get pods  -o custom-columns=N:.metadata.name,I:.spec.containers[0].image  # tableau

# === FILTRER (jq obligatoire, JSONPath ne sait pas) ===
kubectl get pods -o json | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name'
```

### Règle d'or
> **`paths(scalars) | join(".")` + `grep`** = trouvez n'importe quel chemin en 2 secondes.
> Ensuite convertissez en JSONPath. Ne devinez JAMAIS un chemin.
