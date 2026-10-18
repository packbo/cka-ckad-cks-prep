# Guide complet GREP - Rechercher dans les fichiers

## Réponse rapide : Trouver les fichiers contenant "testphrase"

```bash
# Afficher le nom du fichier ET la ligne contenant le texte
grep -ir "testphrase" .

# Afficher SEULEMENT le nom du fichier (sans le contenu)
grep -irl "testphrase" .

# Avec le chemin complet
grep -irl "testphrase" /chemin/absolu
```

## Explication des options grep

### Options de base

```bash
-i    # Case insensitive (ignore majuscules/minuscules)
-r    # Récursif (chercher dans tous les sous-dossiers)
-l    # List files (afficher SEULEMENT le nom du fichier, pas le contenu)
-n    # Numéro de ligne
-v    # Inverse (lignes qui NE contiennent PAS le pattern)
-w    # Mot entier (word boundary)
-c    # Compter les occurrences par fichier
-h    # Supprimer le nom du fichier (afficher seulement le contenu)
-H    # Forcer l'affichage du nom du fichier
```

### Exemples pratiques

#### 1. Recherche de base
```bash
# Chercher "testphrase" dans le répertoire courant (récursif, insensible à la casse)
grep -ir "testphrase" .

# Résultat typique :
# ./mon-fichier.txt:Cette ligne contient testphrase
# ./sous-dossier/autre.txt:Voici une TESTPHRASE en majuscules
```

#### 2. Seulement les noms de fichiers
```bash
# Option -l : list files only
grep -irl "testphrase" .

# Résultat :
# ./mon-fichier.txt
# ./sous-dossier/autre.txt
```

#### 3. Avec numéros de ligne
```bash
grep -irn "testphrase" .

# Résultat :
# ./mon-fichier.txt:42:Cette ligne contient testphrase
# ./sous-dossier/autre.txt:15:Voici une TESTPHRASE en majuscules
#                        ↑
#                   numéro de ligne
```

#### 4. Compter les occurrences par fichier
```bash
grep -irc "testphrase" .

# Résultat :
# ./mon-fichier.txt:3
# ./sous-dossier/autre.txt:1
# ./autre-fichier.txt:0
```

#### 5. Seulement les fichiers avec au moins une occurrence (compter + filtrer)
```bash
grep -irc "testphrase" . | grep -v ":0$"

# Résultat :
# ./mon-fichier.txt:3
# ./sous-dossier/autre.txt:1
```

## Recherches avancées

### Mot entier seulement
```bash
# Chercher "test" mais PAS "testing", "testphrase", etc.
grep -irw "test" .

# Cherche seulement le mot "test" isolé
```

### Pattern regex
```bash
# Recherche avec regex
grep -irE "test(phrase|word|ing)" .

# Cherche "testphrase" OU "testword" OU "testing"
```

### Exclure certains fichiers ou dossiers
```bash
# Exclure les dossiers .git, node_modules, etc.
grep -ir "testphrase" . --exclude-dir={.git,node_modules,vendor}

# Exclure certains types de fichiers
grep -ir "testphrase" . --exclude="*.log" --exclude="*.tmp"

# Inclure seulement certains types
grep -ir "testphrase" . --include="*.yaml" --include="*.yml"

# Exemple Kubernetes : chercher seulement dans les manifests
grep -ir "testphrase" . --include="*.yaml" --include="*.yml"
```

### Contexte autour de la correspondance
```bash
# Afficher 3 lignes AVANT la correspondance
grep -ir "testphrase" . -B 3

# Afficher 3 lignes APRÈS la correspondance
grep -ir "testphrase" . -A 3

# Afficher 3 lignes AVANT et APRÈS (contexte)
grep -ir "testphrase" . -C 3

# Exemple :
grep -ir "error" /var/log -A 5  # Voir les 5 lignes après une erreur
```

### Couleurs et formatage
```bash
# Avec couleurs (souvent activé par défaut)
grep -ir "testphrase" . --color=always

# Sans couleurs
grep -ir "testphrase" . --color=never

# Avec pagination
grep -ir "testphrase" . --color=always | less -R
```

## Cas d'usage Kubernetes

### Chercher dans les manifests YAML
```bash
# Trouver tous les fichiers YAML contenant "nginx"
grep -irl "nginx" . --include="*.yaml" --include="*.yml"

# Trouver les deployments
grep -ir "kind: Deployment" . --include="*.yaml"

# Trouver une image spécifique
grep -ir "image:.*nginx" . --include="*.yaml"

# Trouver un namespace
grep -ir "namespace: kube-system" . --include="*.yaml"

# Trouver des labels
grep -ir "app: mon-app" . --include="*.yaml"

# Trouver des secrets ou configmaps
grep -ir "kind: Secret" . --include="*.yaml"
grep -ir "kind: ConfigMap" . --include="*.yaml"
```

### Chercher dans les logs kubectl
```bash
# Dans les logs d'un pod
kubectl logs mon-pod | grep -i error
kubectl logs mon-pod | grep -i error -A 5  # Avec contexte

# Chercher dans tous les pods d'un namespace
for pod in $(kubectl get pods -o name); do
    echo "=== $pod ==="
    kubectl logs $pod | grep -i "testphrase"
done

# Ou avec xargs
kubectl get pods -o name | xargs -I {} sh -c 'echo "=== {} ===" && kubectl logs {} | grep -i "testphrase"'
```

## Alternatives et outils similaires

### ripgrep (rg) - Version moderne et plus rapide
```bash
# Installer ripgrep
sudo apt install ripgrep

# Même syntaxe, beaucoup plus rapide
rg -i "testphrase"

# Seulement les noms de fichiers
rg -il "testphrase"

# Avec types de fichiers
rg -i "testphrase" -t yaml
rg -i "testphrase" -t yaml -t json

# Exclure des dossiers (automatique pour .git, node_modules, etc.)
rg -i "testphrase"

# Avantages de rg :
# - Plus rapide que grep
# - Ignore automatiquement .git, node_modules, etc.
# - Détection automatique des types de fichiers
# - Coloration par défaut
```

### ack - Alternative à grep
```bash
# Installer ack
sudo apt install ack

# Chercher
ack -i "testphrase"

# Par type de fichier
ack -i "testphrase" --yaml
```

### find + grep (pour plus de contrôle)
```bash
# Chercher dans les fichiers modifiés dans les dernières 24h
find . -name "*.yaml" -mtime -1 -exec grep -l "testphrase" {} \;

# Chercher dans les fichiers de plus de 1MB
find . -name "*.log" -size +1M -exec grep -l "error" {} \;

# Chercher puis compter
find . -name "*.yaml" -exec grep -c "testphrase" {} \; -print
```

## Combinaisons puissantes avec d'autres commandes

### Grep + wc (compter)
```bash
# Nombre de fichiers contenant "testphrase"
grep -irl "testphrase" . | wc -l

# Nombre total d'occurrences
grep -ir "testphrase" . | wc -l

# Nombre d'occurrences dans chaque fichier, trié
grep -irc "testphrase" . | grep -v ":0$" | sort -t: -k2 -nr
```

### Grep + sed (remplacer)
```bash
# Trouver les fichiers contenant "oldvalue" et les remplacer
grep -irl "oldvalue" . --include="*.yaml" | xargs sed -i 's/oldvalue/newvalue/g'

# Attention : toujours faire une backup avant !
grep -irl "oldvalue" . --include="*.yaml" | xargs sed -i.bak 's/oldvalue/newvalue/g'
```

### Grep + awk (extraire)
```bash
# Extraire seulement la partie après ":"
grep -ir "image:" . --include="*.yaml" | awk -F: '{print $3}' | sort -u

# Exemple résultat : liste de toutes les images Docker
```

### Grep + xargs (actions en masse)
```bash
# Trouver tous les fichiers YAML avec "nginx" et les valider
grep -irl "nginx" . --include="*.yaml" | xargs -I {} kubectl apply --dry-run=client -f {}

# Trouver et copier
grep -irl "testphrase" . | xargs -I {} cp {} /destination/
```

## Patterns de recherche utiles

### Chercher des adresses IP
```bash
grep -irE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" .
```

### Chercher des emails
```bash
grep -irE "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b" .
```

### Chercher des URLs
```bash
grep -irE "https?://[^\s]+" .
```

### Chercher des versions (semver)
```bash
grep -irE "\b[0-9]+\.[0-9]+\.[0-9]+\b" .
```

### Chercher dans Kubernetes

```bash
# Chercher tous les secrets
grep -ir "kind: Secret" . --include="*.yaml" -l

# Chercher les resources avec des limits
grep -ir "limits:" . --include="*.yaml" -l

# Chercher les services de type LoadBalancer
grep -ir "type: LoadBalancer" . --include="*.yaml"

# Chercher les hostPath volumes (attention sécurité!)
grep -ir "hostPath:" . --include="*.yaml"

# Chercher les pods privileged (attention sécurité!)
grep -ir "privileged: true" . --include="*.yaml"

# Chercher les images sans tag ou avec :latest
grep -irE "image:.*latest|image: [^:]+$" . --include="*.yaml"
```

## Comparaison : grep vs outil Grep de kubectl

### Dans les logs kubectl
```bash
# Méthode classique (bash grep)
kubectl logs mon-pod | grep -i "error"

# Avec l'outil Grep de Claude Code (si disponible)
# Utilise ripgrep en arrière-plan, plus rapide
```

### Dans les fichiers locaux
```bash
# grep classique (bash)
grep -ir "testphrase" .

# Outil Grep de Claude Code
# (via l'interface, utilise ripgrep optimisé)
```

## Astuces et bonnes pratiques

### 1. Toujours utiliser des guillemets
```bash
# ✅ BON
grep -ir "test phrase" .

# ❌ MAUVAIS (espace non protégé)
grep -ir test phrase .
```

### 2. Échapper les caractères spéciaux
```bash
# Chercher un point littéral
grep -ir "192\.168\.1\.1" .

# Ou utiliser -F pour recherche littérale (pas de regex)
grep -irF "192.168.1.1" .
```

### 3. Combiner plusieurs patterns
```bash
# Chercher "error" OU "exception"
grep -irE "error|exception" .

# Chercher "error" ET "database" (dans le même fichier)
grep -irl "error" . | xargs grep -l "database"
```

### 4. Performance sur gros répertoires
```bash
# Exclure les dossiers volumineux
grep -ir "testphrase" . --exclude-dir={node_modules,.git,vendor,target,build}

# Ou utiliser ripgrep (rg) qui le fait automatiquement
rg -i "testphrase"
```

### 5. Sauvegarder les résultats
```bash
# Sauvegarder la liste des fichiers
grep -irl "testphrase" . > fichiers-trouvés.txt

# Sauvegarder les résultats complets
grep -irn "testphrase" . > résultats-complets.txt

# Sauvegarder avec horodatage
grep -irn "testphrase" . > "résultats-$(date +%Y%m%d-%H%M%S).txt"
```

## Tableau récapitulatif : Options grep les plus utiles

| Option | Description | Exemple |
|--------|-------------|---------|
| `-i` | Ignorer la casse | `grep -i "test" file.txt` |
| `-r` | Récursif | `grep -r "test" .` |
| `-l` | Seulement noms de fichiers | `grep -rl "test" .` |
| `-n` | Avec numéros de ligne | `grep -rn "test" .` |
| `-c` | Compter occurrences | `grep -rc "test" .` |
| `-v` | Inverser (ne contient PAS) | `grep -v "test" file.txt` |
| `-w` | Mot entier | `grep -w "test" file.txt` |
| `-A N` | N lignes après | `grep -A 5 "error" log.txt` |
| `-B N` | N lignes avant | `grep -B 5 "error" log.txt` |
| `-C N` | N lignes avant ET après | `grep -C 5 "error" log.txt` |
| `-E` | Regex étendue | `grep -E "test\|prod" .` |
| `-F` | Recherche littérale (pas regex) | `grep -F "192.168.1.1" .` |
| `--include` | Inclure certains fichiers | `grep -r "test" --include="*.yaml"` |
| `--exclude` | Exclure certains fichiers | `grep -r "test" --exclude="*.log"` |
| `--exclude-dir` | Exclure dossiers | `grep -r "test" --exclude-dir=node_modules` |
| `--color` | Colorier les résultats | `grep --color=always "test" file.txt` |

## Exemples de workflows complets

### Workflow 1 : Audit de sécurité Kubernetes
```bash
# 1. Trouver tous les secrets en clair
grep -ir "kind: Secret" . --include="*.yaml" -l

# 2. Trouver les pods privileged
grep -ir "privileged: true" . --include="*.yaml" -A 2 -B 2

# 3. Trouver les hostPath
grep -ir "hostPath:" . --include="*.yaml"

# 4. Trouver les images :latest
grep -irE "image:.*:latest" . --include="*.yaml"

# 5. Résumé dans un fichier
{
    echo "=== Audit de sécurité $(date) ==="
    echo "=== Secrets ==="
    grep -ir "kind: Secret" . --include="*.yaml" -l
    echo "=== Pods privileged ==="
    grep -ir "privileged: true" . --include="*.yaml" -l
    echo "=== HostPath volumes ==="
    grep -ir "hostPath:" . --include="*.yaml" -l
} > security-audit.txt
```

### Workflow 2 : Trouver et remplacer une image
```bash
# 1. Trouver tous les fichiers utilisant l'ancienne image
grep -irl "nginx:1.20" . --include="*.yaml"

# 2. Vérifier les occurrences
grep -ir "nginx:1.20" . --include="*.yaml" -n

# 3. Remplacer (avec backup)
grep -irl "nginx:1.20" . --include="*.yaml" | xargs sed -i.bak 's/nginx:1.20/nginx:1.21/g'

# 4. Vérifier les changements
diff -u original.yaml original.yaml.bak
```

### Workflow 3 : Debugging d'erreurs dans les logs
```bash
# 1. Chercher toutes les erreurs récentes
kubectl logs mon-pod --since=1h | grep -i error

# 2. Avec contexte
kubectl logs mon-pod --since=1h | grep -i error -C 5

# 3. Compter par type
kubectl logs mon-pod --since=1h | grep -i error | awk '{print $4}' | sort | uniq -c

# 4. Sauvegarder pour analyse
kubectl logs mon-pod --since=1h | grep -i error -C 10 > errors-$(date +%Y%m%d).log
```

## Aide-mémoire rapide

```bash
# Chercher récursivement, ignorer casse, afficher fichier:ligne
grep -ir "texte" .

# Seulement les noms de fichiers
grep -irl "texte" .

# Avec numéros de ligne
grep -irn "texte" .

# Dans certains types de fichiers
grep -ir "texte" . --include="*.yaml"

# Exclure des dossiers
grep -ir "texte" . --exclude-dir={.git,node_modules}

# Avec contexte
grep -ir "texte" . -C 3

# Compter
grep -irc "texte" .

# Regex
grep -irE "texte|autre" .

# Mot entier
grep -irw "texte" .
```
