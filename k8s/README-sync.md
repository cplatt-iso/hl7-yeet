# Sync env from Docker Compose to Kubernetes

This small helper extracts values from the project's `.env` file and constructs
`ConfigMap` and `Secret` YAML files for the `yeeter` namespace, then optionally applies them.

Usage:

```bash
# Make executable
chmod +x k8s/sync_from_docker_compose.sh

# Run
./k8s/sync_from_docker_compose.sh
```

What it does:
- Reads keys from `.env`
- Writes `k8s/generated/yeeter-configmap.yaml` and `k8s/generated/yeeter-secret.yaml`
- Backs up existing `yeeter-config` and `yeeter-secrets` from the cluster
- Optionally applies the generated resources to the cluster

Notes:
- Only a limited set of keys are processed (see `SECRET_KEYS` and `CONFIG_KEYS` in the script).
- If you need extra keys, edit the arrays in the script.
- You must have `kubectl` configured to the target cluster when applying.
