# Environment check

The background setup may still be finishing (cluster creation takes 2-4 min). Verify:

```bash
cd /root/cka-ckad-cks-prep/cka-sim
./run.sh status
```

If the cluster is still coming up, watch it settle:

```bash
kubectl get nodes -w
```

Wait until all 3 nodes are `Ready` (Ctrl-C to stop watching).

If anything failed, check the setup log: `tail -30 /var/log/cka-prep-setup.log`,
or simply re-run the bootstrap (it is idempotent):

```bash
curl -fsSL https://raw.githubusercontent.com/packbo/cka-ckad-cks-prep/main/killercoda/bootstrap.sh | bash
```
