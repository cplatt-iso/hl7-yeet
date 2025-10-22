#!/usr/bin/env bash
# Migrate PostgreSQL database from Docker Compose to Kubernetes
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/k8s/db-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="$BACKUP_DIR/yeeter_db_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

# Database credentials (from .env)
DB_USER="${POSTGRES_USER:-yeeter_user}"
DB_NAME="${POSTGRES_DB:-hl7_yeeter_db}"
DB_PASS="${POSTGRES_PASSWORD:-yeeter_pw}"

echo "=== HL7 Yeeter Database Migration ==="
echo ""

# Step 1: Check if Docker postgres container exists or volume is accessible
echo "Step 1: Looking for Docker PostgreSQL data..."
DOCKER_VOLUME="databases_postgres_data"

if ! docker volume inspect "$DOCKER_VOLUME" > /dev/null 2>&1; then
    echo "❌ Docker volume '$DOCKER_VOLUME' not found!"
    echo "Available volumes:"
    docker volume ls | grep postgres
    exit 1
fi

echo "✅ Found Docker volume: $DOCKER_VOLUME"
echo ""

# Step 2: Start a temporary postgres container to dump the data
echo "Step 2: Creating database dump from Docker volume..."
echo "Dump file: $DUMP_FILE"

docker run --rm \
    -v "$DOCKER_VOLUME:/var/lib/postgresql/data:ro" \
    -e POSTGRES_PASSWORD="$DB_PASS" \
    postgres:15-alpine \
    sh -c "pg_dump -U $DB_USER -d $DB_NAME" > "$DUMP_FILE" 2>/dev/null || {
        echo "❌ Failed to dump from Docker volume. Trying alternative method..."
        
        # Alternative: If the old container still exists
        CONTAINER_NAME="yeeter_postgres"
        if docker ps -a | grep -q "$CONTAINER_NAME"; then
            echo "Found old container $CONTAINER_NAME, attempting dump..."
            docker start "$CONTAINER_NAME" 2>/dev/null || true
            sleep 3
            docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$DUMP_FILE"
            docker stop "$CONTAINER_NAME" 2>/dev/null || true
        else
            echo "❌ No accessible PostgreSQL data found"
            exit 1
        fi
    }

if [ ! -s "$DUMP_FILE" ]; then
    echo "❌ Dump file is empty!"
    exit 1
fi

echo "✅ Database dump created ($(du -h "$DUMP_FILE" | cut -f1))"
echo ""

# Step 3: Import into k8s PostgreSQL
echo "Step 3: Importing dump into Kubernetes PostgreSQL..."

K8S_NAMESPACE="yeeter"
K8S_POD=$(kubectl get pods -n "$K8S_NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')

if [ -z "$K8S_POD" ]; then
    echo "❌ No PostgreSQL pod found in namespace $K8S_NAMESPACE"
    exit 1
fi

echo "Found k8s pod: $K8S_POD"

# Copy dump file to pod
echo "Copying dump file to pod..."
kubectl cp "$DUMP_FILE" "$K8S_NAMESPACE/$K8S_POD:/tmp/restore.sql"

# Restore the dump
echo "Restoring database..."
kubectl exec -n "$K8S_NAMESPACE" "$K8S_POD" -- psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/restore.sql

# Clean up
kubectl exec -n "$K8S_NAMESPACE" "$K8S_POD" -- rm /tmp/restore.sql

echo ""
echo "✅ Database migration complete!"
echo ""
echo "Backup saved to: $DUMP_FILE"
echo ""
echo "Verify the migration:"
echo "  kubectl exec -n yeeter deployment/postgres -- psql -U $DB_USER -d $DB_NAME -c '\\dt'"
echo ""
