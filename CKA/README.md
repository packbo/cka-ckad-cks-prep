# Guide de Préparation CKA (Certified Kubernetes Administrator)

## Structure du Dossier

```
CKA/
├── README.md                    # Ce fichier - Vue d'ensemble
├── setup-environnement.md       # Configuration examen (alias, vim, tips)
├── reminder.md                  # Tous les concepts et commandes essentiels
├── exercices-pratiques.md       # Exercices par thème + simulation examen
└── scenarios-avances.md         # Scénarios complexes + Helm/Kustomize
```

## Plan d'Étude Recommandé

### Semaine 1-2: Fondamentaux
- [ ] Lire `setup-environnement.md` et configurer votre env
- [ ] Étudier `reminder.md` sections 1-7 (Pods → RBAC)
- [ ] Faire `exercices-pratiques.md` Ex 1-18
- [ ] **Objectif:** Créer pods, deployments, services les yeux fermés

### Semaine 3-4: Concepts Avancés
- [ ] Étudier `reminder.md` sections 8-13 (NetworkPolicy → Jobs)
- [ ] Faire `exercices-pratiques.md` Ex 19-23
- [ ] Lire `scenarios-avances.md` scénarios 1-5
- [ ] **Objectif:** Maîtriser scheduling, storage, networking

### Semaine 5-6: Administration Cluster
- [ ] Étudier `reminder.md` sections 14-16 (Upgrade, ETCD, Troubleshooting)
- [ ] Lire `scenarios-avances.md` scénarios 6-9
- [ ] Pratiquer upgrade cluster complet 5+ fois
- [ ] **Objectif:** Upgrade et backup/restore en <15 min

### Semaine 7-8: Practice Intensive
- [ ] Faire simulation complète dans `exercices-pratiques.md`
- [ ] Refaire TOUS les scénarios avancés
- [ ] Killer.sh practice exam (inclus avec inscription)
- [ ] Timer: 2h pour 15-20 questions
- [ ] **Objectif:** Score >80% consistant

## Distributions du Temps d'Examen (2 heures)

| Domaine | % Examen | Temps |
|---------|----------|-------|
| Storage & Volumes | 10% | 12 min |
| Troubleshooting | 30% | 36 min |
| Workloads & Scheduling | 15% | 18 min |
| Cluster Architecture | 25% | 30 min |
| Services & Networking | 20% | 24 min |

## Checklist Avant l'Examen

### Compétences Techniques
- [ ] Créer pod/deployment en <2 min
- [ ] Exposer service en <1 min
- [ ] Créer PV/PVC en <3 min
- [ ] Configurer RBAC en <5 min
- [ ] Upgrade node en <10 min
- [ ] Backup/restore ETCD en <8 min
- [ ] Debug pod failing en <5 min

### Connaissances
- [ ] Savoir chercher dans kubernetes.io rapidement
- [ ] Connaître les alias par coeur
- [ ] Comprendre architecture Kubernetes (etcd, api-server, scheduler...)
- [ ] Savoir lire journalctl et systemctl logs

### Pratique
- [ ] Killer.sh exam (2 fois minimum)
- [ ] 100+ exercices pratiques
- [ ] 20+ scénarios de troubleshooting

## Commandes à Mémoriser ABSOLUMENT

```bash
# Setup (début examen - 2 min)
alias k=kubectl
complete -F __start_kubectl k
export do="--dry-run=client -o yaml"
export now="--force --grace-period=0"

# Top 15 commandes
k run nginx --image=nginx
k create deploy nginx --image=nginx --replicas=3
k expose pod nginx --port=80
k scale deploy nginx --replicas=5
k set image deploy/nginx nginx=nginx:1.20
k rollout undo deploy/nginx
k create cm config --from-literal=key=value
k create secret generic secret --from-literal=pass=123
k create sa mysa
k create role myrole --verb=get,list --resource=pods
k create rolebinding bind --role=myrole --user=john
k label node node1 key=value
k taint node node1 key=value:NoSchedule
k drain node1 --ignore-daemonsets
k cordon/uncordon node1
```

## Resources Kubernetes.io Essentielles

**Bookmarks à créer pendant l'examen:**

1. **Cheat Sheet:** kubernetes.io/docs/reference/kubectl/cheatsheet/
2. **Pod Examples:** kubernetes.io/docs/concepts/workloads/pods/
3. **Service Examples:** kubernetes.io/docs/concepts/services-networking/service/
4. **PV/PVC:** kubernetes.io/docs/concepts/storage/persistent-volumes/
5. **RBAC:** kubernetes.io/docs/reference/access-authn-authz/rbac/
6. **NetworkPolicy:** kubernetes.io/docs/concepts/services-networking/network-policies/
7. **Kubeadm Upgrade:** kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/

## Erreurs Mortelles à Éviter

1. ❌ **Ne PAS vérifier le context** → travail dans mauvais cluster
2. ❌ **Écrire YAML à la main** → perte de temps + erreurs
3. ❌ **Bloquer sur une question** → flag et continue!
4. ❌ **Ne pas vérifier le résultat** → perte de points
5. ❌ **Oublier le namespace** → ressource non trouvée

## Stratégie Pendant l'Examen

### Première Lecture (5 min)
- Lire TOUTES les questions
- Marquer le poids de chaque question (2%, 4%, 7%...)
- Identifier facile/moyen/difficile

### Première Passe (60 min)
- Faire TOUTES les questions faciles (pods, deploys, services)
- Ne PAS perdre de temps sur les difficiles
- Vérifier chaque réponse immédiatement

### Deuxième Passe (40 min)
- Questions moyennes (RBAC, storage, scheduling)
- Prendre le temps de bien faire
- Utiliser kubernetes.io si besoin

### Troisième Passe (15 min)
- Questions difficiles flaggées
- Troubleshooting complexes
- NetworkPolicy, ETCD restore

### Révision (5 min)
- Re-vérifier les questions à haut %
- Test rapide des services créés
- Check que tout est dans le bon namespace/context

## Score et Résultats

- **Score minimum:** 66%
- **Durée validité:** 3 ans
- **Retake:** 1 gratuit inclus
- **Résultats:** 24h après examen

## Tips de Performance

### Vitesse
- Tab completion est votre ami
- Utiliser `$do` systématiquement
- Copier-coller depuis kubernetes.io (autorisé!)
- Ne pas perdre temps à formatter YAML

### Précision
- Toujours faire `k describe` après création
- Vérifier Events pour erreurs
- Tester fonctionnel (curl, exec)

### Time Management
- 7 min maximum par question
- Si bloqué >5 min → flag et next
- Revenir à la fin

## Commandes de Debug Essentielles

```bash
# Pod issues
k describe pod <name>
k logs <pod> [-c container] [--previous]
k get events --sort-by=.metadata.creationTimestamp

# Service issues
k get endpoints <service>
k describe svc <service>

# Node issues
k describe node <name>
ssh node1
systemctl status kubelet
journalctl -u kubelet

# Cluster issues
k cluster-info
k get cs  # component status
crictl ps  # runtime level
```

## Ressources Complémentaires

### Practice Exams
- **Killer.sh** (inclus avec inscription) - MUST DO
- **KodeKloud CKA Course** - Excellent pour practice
- **GitHub:** Chercher "CKA exercises" pour plus

### Documentation Officielle
- **kubernetes.io/docs** - LA référence
- **github.com/kubernetes/kubernetes** - Source code

### Communauté
- **r/kubernetes** - Reddit community
- **Kubernetes Slack** - #cka channel
- **CNCF Slack** - Aide et support

## Derniers Mots

**La clé du succès CKA:**
1. **Practice, practice, practice** - 100+ heures minimum
2. **Speed** - Générer YAML automatiquement
3. **Documentation** - Maîtriser kubernetes.io
4. **Time management** - Ne pas bloquer
5. **Verification** - Toujours vérifier

**Vous êtes capable!** Le CKA n'est pas un exam de connaissances théoriques mais de compétences pratiques. Si vous pouvez faire les exercices de ce dossier rapidement, vous êtes prêt.

---

**Note:** Ce guide est basé sur le format CKA 2024/2025. Vérifier les mises à jour sur kubernetes.io et CNCF.

Bon courage! 🚀 Vous allez réussir! 💪
