# CKAD exam definitions (full-exam.yaml, web-exam.yaml)

Drop CKAD scenarios in `scenarios/ckad/` and reference their ids here.

Official blueprint **CKAD v1.37** (2h):

| Domain | Weight |
|--------|--------|
| Application Design and Build (multi-container pods: sidecar/init, volumes) | 20% |
| Application Deployment (blue/green, canary, rolling updates, Helm, Kustomize) | 20% |
| Application Observability and Maintenance (probes, logs, deprecations) | 15% |
| Application Environment, Configuration and Security (CM/Secrets, SA, limits, SecurityContext, CRD) | 25% |
| Services and Networking (NetworkPolicies, services, Ingress) | 20% |

Many CKA-bank scenarios already fit CKAD (workloads, services, config) —
`./run.sh --cert cka list` and reuse ids across exam files is fine.
