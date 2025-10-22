#!/usr/bin/env bash
# Extract environment settings from the project's .env and docker-compose.yml
# and generate Kubernetes ConfigMap and Secret YAML, then apply them.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
DC_FILE="$PROJECT_ROOT/docker-compose.yml"
OUT_DIR="$PROJECT_ROOT/k8s/generated"
K8S_NAMESPACE="yeeter"

mkdir -p "$OUT_DIR"

echo "Reading environment from $ENV_FILE"
if [ ! -f "$ENV_FILE" ]; then
  echo "No .env file found at $ENV_FILE"
  exit 1
fi

# Load env into a subshell associative array (POSIX: use basic parsing)
declare -A env_map
while IFS='=' read -r key value; do
  # Skip comments and empty lines
  [[ "$key" =~ ^# ]] && continue
  [ -z "$key" ] && continue
  key=$(echo "$key" | tr -d '[:space:]')
  # Trim surrounding quotes from value
  value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
  env_map["$key"]="$value"
done < <(grep -E "^[A-Za-z0-9_]+=" "$ENV_FILE" || true)

# Build ConfigMap and Secret YAMLs
CONFIGMAP_FILE="$OUT_DIR/yeeter-configmap.yaml"
SECRET_FILE="$OUT_DIR/yeeter-secret.yaml"

cat > "$CONFIGMAP_FILE" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: yeeter-config
  namespace: $K8S_NAMESPACE
data:
EOF

# ConfigMap keys (non-sensitive)
CONFIG_KEYS=(
  FLASK_ENV
  JWT_ACCESS_TOKEN_EXPIRES_HOURS
  VITE_API_URL
  VITE_SOCKET_URL
  DATABASE_URL
)

for k in "${CONFIG_KEYS[@]}"; do
  v="${env_map[$k]:-}"
  if [ -n "$v" ]; then
    echo "  $k: \"$v\"" >> "$CONFIGMAP_FILE"
  fi
done

# Secrets
cat > "$SECRET_FILE" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: yeeter-secrets
  namespace: $K8S_NAMESPACE
type: Opaque
data:
EOF

SECRET_KEYS=(
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_DB
  JWT_SECRET_KEY
  GOOGLE_API_KEY
  VITE_GOOGLE_CLIENT_ID
)

for k in "${SECRET_KEYS[@]}"; do
  v="${env_map[$k]:-}"
  if [ -n "$v" ]; then
    b64=$(echo -n "$v" | base64 -w 0)
    echo "  $k: $b64" >> "$SECRET_FILE"
  fi
done

# Backup current k8s resources
BACKUP_DIR="$OUT_DIR/backup-$(date +%Y%m%d%H%M%S)"
mkdir -p "$BACKUP_DIR"

kubectl -n "$K8S_NAMESPACE" get configmap yeeter-config -o yaml > "$BACKUP_DIR/yeeter-config.yaml" 2>/dev/null || true
kubectl -n "$K8S_NAMESPACE" get secret yeeter-secrets -o yaml > "$BACKUP_DIR/yeeter-secrets.yaml" 2>/dev/null || true

echo "ConfigMap written to $CONFIGMAP_FILE"
echo "Secret written to $SECRET_FILE"
echo "Backup (if any) saved to $BACKUP_DIR"

echo "Apply to cluster? (y/N)"
read -r yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
  kubectl apply -f "$CONFIGMAP_FILE"
  kubectl apply -f "$SECRET_FILE"
  echo "Applied to namespace $K8S_NAMESPACE"
else
  echo "Not applied. You can apply the files manually with:"
  echo "  kubectl apply -f $CONFIGMAP_FILE"
  echo "  kubectl apply -f $SECRET_FILE"
fi
