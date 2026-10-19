# CKA coverage — official curriculum v1.37 → scenario bank

Audit date: 2026-10 · Source: github.com/cncf/curriculum (CKA_Curriculum_v1.37.pdf)

## 1. Cluster Architecture, Installation & Configuration — 25%

| Competency | Scenario |
|------------|----------|
| RBAC (Roles/Bindings/ClusterRoles/SA) | `role-binding` |
| kubeadm install & join (tokens) | `kubeadm-token` |
| etcd backup & restore / HA | `etcd-backup` |
| Static pods / manifests dir | `static-pod` |
| Helm / Kustomize | `kustomize-apply` (Helm: `../guides/helm-guide-complet.md`) |
| Node maintenance (drain, taints) | `drain-uncordon`, `taint-worker` |
| Full `kubeadm upgrade`, CNI/CSI plugin install | NOT kind-simulable → `../CKA/reminder.md` §14 + guides |

## 2. Workloads & Scheduling — 15%

| Competency | Scenario |
|------------|----------|
| Deployments, scale, rollouts | `create-deploy`, `rollout-rollback`, `rolling-strategy`, `extract-image-deploy` |
| Jobs / CronJobs | `job-completions`, `cronjob-every-2min` |
| Multi-container pods | `sidecar-logging`, `init-container` |
| Configure via ConfigMaps/Secrets | `env-configmap`, `secret-volume` |
| Scheduling (selector/affinity/taints/DS) | `node-selector-schedule`, `node-affinity`, `taint-worker`, `daemonset-node-labels`, `resources-limits` |

## 3. Services & Networking — 20%

| Competency | Scenario |
|------------|----------|
| Services (ClusterIP/NodePort/headless) | `expose-nodeport`, `headless-service` |
| Ingress | `ingress-path` |
| NetworkPolicies | `network-policy`, `netpol-default-deny` |
| Liveness/readiness probes | `probe-readiness` |
| Service connectivity troubleshooting | `service-no-endpoints` |

## 4. Storage — 10%

| Competency | Scenario |
|------------|----------|
| PV/PVC lifecycle | `pvc-mount`, `pvc-rwo` |
| StorageClasses | `storage-class` |
| Storage-related troubleshooting | `fix-pending-pvc` |

## 5. Troubleshooting — 30%

| Competency | Scenario |
|------------|----------|
| Pod failures (CrashLoop, ImagePull, Pending) | `fix-crashloop`, `fix-image-pull`, `fix-pending-pvc` |
| Service/network debugging | `service-no-endpoints` |
| Events, logs, describe methods | `first-pod`, `inspect-pod`, `explain-fields` (guided basics) |
| Labels/annotations | `delete-label` |
| Nodes & control plane | `drain-uncordon`, `etcd-backup` |

## Kind limitations (by design)

`kubeadm upgrade` of node packages, CNI plugin installation and kubelet
systemd debugging require VMs, not kind containers. These competencies are
covered by `../CKA/reminder.md` (§14 upgrade, §16 troubleshooting) and the
guides; everything else in the blueprint is hands-on above.

## Gap analysis additions (2026-10, inspired by sv222/k8s-operations-runbook)

| Topic | Scenario |
|-------|----------|
| StatefulSet (stable identity, headless svc) | `statefulset-create` |
| Horizontal Pod Autoscaler | `hpa-autoscale` |
| ResourceQuota + LimitRange | `resource-quota` |
| imagePullSecrets (private registry) | `image-pull-secret` |
