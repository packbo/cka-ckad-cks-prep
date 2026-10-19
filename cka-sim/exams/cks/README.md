# CKS exam definitions (full-exam.yaml, web-exam.yaml)

Drop CKS scenarios in `scenarios/cks/` and reference their ids here.
CKS requires a passed CKA; several topics need node/OS access (AppArmor,
seccomp, kubelet config) — the kind cluster exposes control-plane + workers
via `docker exec`.

Official blueprint **CKS v1.34** (exam env v1.35, 2h):

| Domain | Weight |
|--------|--------|
| Cluster Setup (NetworkPolicies, CIS benchmark, Ingress TLS, metadata protection) | 15% |
| Cluster Hardening (RBAC, service accounts, API access, upgrades) | 15% |
| System Hardening (host OS footprint, least privilege, AppArmor/seccomp) | 10% |
| Minimize Microservice Vulnerabilities (Pod Security Standards, secrets, isolation) | 20% |
| Supply Chain Security (image footprint, SBOM, permitted registries, static analysis) | 20% |
| Monitoring, Logging and Runtime Security (audit logs, behavioral analytics, immutability) | 20% |
