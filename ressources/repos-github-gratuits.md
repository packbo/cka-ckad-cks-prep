# Repos GitHub gratuits — CKA / CKAD / CKS

Tous les repos vérifiés et gratuits pour préparer les certifications. Vérifié octobre 2026.

## Officiel (à consulter en premier)

| Repo | Description |
|---|---|
| [cncf/curriculum](https://github.com/cncf/curriculum) | **Programmes officiels** des examens (PDF CKA/CKAD/CKS + toutes les certs CNCF). La référence pour savoir exactement ce qui est au programme |
| [kubernetes/website](https://github.com/kubernetes/website) | Source de kubernetes.io — la SEULE doc autorisée pendant l'examen. Entraîne-toi à y naviguer vite |

## CKA

| Repo | ★ | Description |
|---|---|---|
| [walidshaari/Kubernetes-Certified-Administrator](https://github.com/walidshaari/Kubernetes-Certified-Administrator) | 4.5k | La liste curatée de référence : objectifs liés à kubernetes.io, labs kubeadm, guide troubleshooting, tactiques jour d'examen |
| [StenlyTU/K8s-training-official](https://github.com/StenlyTU/K8s-training-official) | — | 50+ tâches pratiques de difficulté croissante, basées sur la doc officielle |
| [kelseyhightower/kubernetes-the-hard-way](https://github.com/kelseyhightower/kubernetes-the-hard-way) | 25k+ | Monter un cluster à la main (CA, certs, étcd, composants). Excellent pour le domaine *Cluster Architecture 25%* |
| [ahmetb/kubectl-aliases](https://github.com/ahmetb/kubectl-aliases) | 30k+ | ~200 alias kubectl (cf. notre `guides/alias-raccourcis-examen.md`) |

## CKAD

| Repo | ★ | Description |
|---|---|---|
| [dgkanatsios/CKAD-exercises](https://github.com/dgkanatsios/CKAD-exercises) | 10.2k | **Exercices par domaine** (core concepts, pod design, config, observability, services, state, helm, CRD). **Cloné localement** dans `ressources/CKAD-exercises/` |

## CKS (prérequis : CKA valide)

| Repo | ★ | Description |
|---|---|---|
| [walidshaari/Certified-Kubernetes-Security-Specialist](https://github.com/walidshaari/Certified-Kubernetes-Security-Specialist) | 2.1k | La liste curatée CKS de référence (6 domaines, ressources triées par statut "autorisé examen") |
| [killer-sh/cks-challenge-series](https://github.com/killer-sh/cks-challenge-series) | — | Série de challenges CKS par Kim Wüstkamp (créateur de killer.sh) |
| [stackrox/Kubernetes_Security_Specialist_Study_Guide](https://github.com/stackrox/Kubernetes_Security_Specialist_Study_Guide) | — | Guide d'étude condensé |
| [ijelliti/CKSS-Certified-Kubernetes-Security-Specialist](https://github.com/ijelliti/CKSS-Certified-Kubernetes-Security-Specialist) | — | Notes + ressources par objectif |
| [vedmichv/CKS-Certified-Kubernetes-Security-Specialist](https://github.com/vedmichv/CKS-Certified-Kubernetes-Security-Specialist) | — | Resources par domaine |
| [moabukar/CKS-Exercises-Certified-Kubernetes-Security-Specialist](https://github.com/moabukar/CKS-Exercises-Certified-Kubernetes-Security-Specialist) | — | Exercices pratiques CKS |
| [madhuakula/kubernetes-goat](https://github.com/madhuakula/kubernetes-goat) | 4k+ | Environnement Kubernetes volontairement vulnérable — parfait pour pratiquer la sécurité en conditions réelles (trivy, falco, audit) |
| [aquasecurity/trivy](https://github.com/aquasecurity/trivy) | — | Scanner de vulnérabilités — outil AU PROGRAMME CKS (doc autorisée à l'examen) |

## Outils pour s'entraîner en local

| Repo | Description |
|---|---|
| [kubernetes-sigs/kind](https://github.com/kubernetes-sigs/kind) | Cluster multi-nœuds dans Docker — **déjà utilisé par notre `cka-sim`** |
| [k3d-io/k3d](https://github.com/k3d-io/k3d) | k3s dans Docker — plus léger que kind, idéal machine modeste |
| [kubernetes/minikube](https://github.com/kubernetes/minikube) | Cluster local mono-nœud |
| [ContainerSolutions/kubernetes-examples](https://github.com/ContainerSolutions/kubernetes-examples) | Exemples de troubleshooting par cas d'usage |

## Playgrounds gratuits en ligne (rappel)

| Plateforme | Limite | Usage |
|---|---|---|
| [Killercoda](https://killercoda.com) | 1h/session | Drill quotidien multi-nœuds |
| [killer.sh](https://killer.sh) | 2 sessions avec l'examen | Simulation réelle |
| [Play with Kubernetes](https://play-with-k8s.com) | 4h/session | Pratique `kubeadm init`/`join` |
| [iximiuz Labs](https://iximiuz.com) | ~1h/session | Parcours guidés |
| [Sadservers](https://sadservers.com) | scénarios | Troubleshooting Linux + k8s |
| GitHub Codespaces | 120 core-h/mois | **cka-sim dans le navigateur** (kind fonctionne) |
| [OCI Always Free](https://www.oracle.com/cloud/free/) | 4 ARM cœurs / 24 Go RAM forever | Cluster k3s/kubeadm 24/7 |

## Comment utiliser tout ça

1. **Lire l'objectif officiel** → [cncf/curriculum](https://github.com/cncf/curriculum) (PDF à jour)
2. **Étudier le point** → walidshaari (CKA) ou CKAD-exercises (CKAD) avec kubernetes.io ouvert
3. **Pratiquer** → cluster kind local (`cka-sim`) ou Killercoda
4. **Se tester** → `./cka-sim/run.sh exam` puis killer.sh à J-7
