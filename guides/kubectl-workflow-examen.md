# Workflow Examen CKA - Chaîne d'actions par question

> Ce guide décrit la **méthode** à appliquer à CHAQUE question de l'examen, du début
> à la fin. La régularité du workflow fait gagner plus de temps que la connaissance
> brute. À pratiquer jusqu'à l'automatisme.

---

## Phase 0 — Setup (1 fois, 2 minutes au début)

```bash
alias k=kubectl
complete -F __start_kubectl k
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"
echo 'set ts=2 sw=2 et' >> ~/.vimrc
```

---

## Phase 1 — Lire la question (30 secondes)

Pendant la lecture, identifier **3 choses** :

1. **Quel cluster/context ?** → souvent plusieurs clusters dans l'examen
2. **Quel namespace ?** → précisé ou implicite (`default`)
3. **Quel type de réponse ?** → créer / modifier / extraire une info / debug

> Notez le % de la question (2%, 4%, 7%...). Faites d'abord les gros % faciles.

---

## Phase 2 — Se positionner (10 secondes)

**AVANT TOUTE action** — c'est l'erreur fatale la plus courante :

```bash
# 1. Bon cluster ?
kubectl config use-context <context-demandé>

# 2. Vérifier où on est
kubectl config current-context

# 3. Se placer dans le bon namespace
kubectl config set-context --current --namespace=<ns-demandé>

# 4. Confirmer le namespace
kubectl config view --minify | grep namespace
```

---

## Phase 3 — Exécuter selon le type de tâche

### Type A : Créer une ressource (Pod, Deploy, Service...)

**RÈGLE D'OR : ne jamais écrire le YAML à la main.**

```bash
# Générer avec --dry-run
kubectl create deploy nginx --image=nginx --replicas=3 $do > deploy.yaml

# Éditer si besoin
vim deploy.yaml

# Appliquer
kubectl apply -f deploy.yaml
```

Génération rapide de chaque type :
```bash
k run nginx --image=nginx $do > pod.yaml
k create deploy nginx --image=nginx $do > deploy.yaml
k expose pod nginx --port=80 --type=NodePort $do > svc.yaml
k create cm cfg --from-literal=k=v $do > cm.yaml
k create secret generic s --from-literal=p=secret $do > secret.yaml
k create sa mysa $do > sa.yaml
k create role r --verb=get,list --resource=pods $do > role.yaml
k create job j --image=busybox $do > job.yaml
```

### Type B : Modifier une ressource existante

```bash
# Éditer en place (rapide pour petite modif)
kubectl edit deploy nginx

# Pour modif plus complexe : exporter, modifier, réappliquer
kubectl get deploy nginx -o yaml > deploy.yaml
vim deploy.yaml
kubectl replace -f deploy.yaml
```

### Type C : Extraire une information précise (JSONPath)

**Workflow en 2 étapes — ne devinez jamais le chemin :**

```bash
# 1. Touver le chemin
kubectl get pod X -o json | jq -r 'paths(scalars)|join(".")' | grep -i <champ>

# 2. Extraire
kubectl get pod X -o jsonpath='{.chemin.trouvé}'
```

Voir `jsonpath-antiseche-express.md` pour tous les patterns prêts à copier.

### Type D : Debug / Troubleshooting (30% de l'examen !)

```bash
# Pod en problème
kubectl describe pod X                      # → section Events
kubectl logs X                              # logs actuels
kubectl logs X --previous                   # logs avant crash
kubectl logs X -c <container>               # multi-container
kubectl get events --sort-by=.metadata.creationTimestamp

# Pod ne démarre pas / ImagePullBackOff
kubectl describe pod X | grep -A5 Events

# Service sans endpoints (pods non connectés)
kubectl get endpoints <svc>
kubectl get pods --show-labels              # labels = selector du svc ?
kubectl describe svc <svc>                  # vérifier spec.selector

# Node NotReady
kubectl describe node X
ssh <node> ; systemctl status kubelet ; journalctl -u kubelet
```

---

## Phase 4 — Vérifier (30 secondes, OBLIGATOIRE)

**Ne jamais passer à la question suivante sans vérifier :**

```bash
# La ressource existe-t-elle et est-elle saine ?
kubectl get deploy nginx
kubectl get pods

# Si pod créé → Events propres ?
kubectl describe pod X | grep -A10 Events

# Si service créé → endpoints présents ?
kubectl get endpoints <svc>

# Test fonctionnel quand possible
kubectl run tmp --image=busybox -it --rm -- wget -O- <svc>:<port>
```

---

## Phase 5 — Ranger et passer

```bash
# Nettoyer les pods temporaires de debug
kubectl delete pod tmp --force --grace-period=0   # ou $now

# Revenir au namespace par défaut si la question suivante l'exige
kubectl config set-context --current --namespace=default
```

---

## Workflow résumé en une image

```
┌─ LIRE (cluster? ns? %?) ─────────────────────┐
│                                               │
├─ SE POSITIONNER (use-context + namespace) ────┤
│                                               │
├─ EXÉCUTER                                     │
│   • créer      → $do + edit + apply           │
│   • modifier   → kubectl edit / replace       │
│   • extraire   → paths(scalars) + jsonpath    │
│   • debug      → describe/logs/events         │
│                                               │
├─ VÉRIFIER (get + describe Events) ────────────┤
│                                               │
└─ RANGER + question suivante ──────────────────┘
```

---

## Gestion du temps (2 heures)

| Bloc | Durée | Action |
|------|-------|--------|
| Lecture | 5 min | Lire TOUTES les questions, noter les % |
| Passe 1 | 60 min | Questions faciles (pods/deploys/svc) |
| Passe 2 | 40 min | Questions moyennes (RBAC, storage, scheduling) |
| Passe 3 | 15 min | Questions difficiles flaggées |
| Révision | 5 min | Re-vérifier les questions à haut % |

**Règle absolue :** si bloqué >5 min → **flag + question suivante**. Revenir plus tard.

---

## Checklist anti-erreurs (à relire si doute)

- [ ] Bon `context` ? (`k config current-context`)
- [ ] Bon `namespace` ? (`k config view --minify | grep namespace`)
- [ ] Le selector du Service matche les labels du Pod ?
- [ ] Le PV/PVC a le bon `accessModes` et la bonne taille ?
- [ ] Pour un NodePort → port entre 30000-32767
- [ ] NetworkPolicy → copier le template de kubernetes.io
- [ ] RBAC → bien distinguer `role`/`clusterrole` et `--user`/`--serviceaccount`
- [ ] Upgrade → drainer AVANT, uncordon APRÈS
- [ ] ETCD restore → modifier le fichier static pod `/etc/kubernetes/manifests/etcd.yaml`

---

## Réflexes `kubectl` qui sauvent du temps

```bash
k explain pod.spec.containers.resources --recursive   # doc sans internet
k explain pod.spec --recursive | grep -i image         # trouver un champ
k get all -A                                            # vue d'ensemble
k get <res> -o yaml | kubectl replace -f -             # modif rapide en pipe
k label node X key=val --overwrite                      # corriger un label
kubectl run tmp --rm -it --image=busybox -- sh         # shell jetable pour tester
```
