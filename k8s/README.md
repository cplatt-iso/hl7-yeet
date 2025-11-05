# HL7 Yeeter - Kubernetes Deployment

This directory contains Kubernetes manifests for deploying HL7 Yeeter on k3s.

## Files

- `namespace.yaml` - Creates the `yeeter` namespace
- `configmap.yaml` - ConfigMap and Secret with environment variables and credentials
- `pvc.yaml` - PersistentVolumeClaims for PostgreSQL and application data
- `postgres.yaml` - PostgreSQL deployment and services (internal + NodePort)
- `app.yaml` - Application deployment and NodePort service
- `worker.yaml` - RabbitMQ worker deployment
- `deploy.sh` - Automated deployment script

## Quick Start

### Prerequisites

1. k3s cluster running
2. kubectl configured
3. Docker installed (for building image)

### Deploy

```bash
# From project root
./k8s/deploy.sh
```

This script will:
1. Build the application and worker Docker images locally
2. Import both images to k3s
3. Apply all Kubernetes manifests
4. Wait for pods to be ready
5. Display access information

### Manual Deployment

If you prefer manual steps:

```bash
# Build and import images
docker build -t hl7-yeeter:latest .
docker build -t hl7-yeeter-worker:latest -f Dockerfile.worker .
docker save hl7-yeeter:latest | sudo k3s ctr images import -
docker save hl7-yeeter-worker:latest | sudo k3s ctr images import -

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/app.yaml
kubectl apply -f k8s/worker.yaml

# Check status
kubectl get pods -n yeeter
kubectl get svc -n yeeter
```

## Configuration

### Environment Variables

Edit `configmap.yaml` to change:

- `FLASK_ENV` - Flask environment (production/development)
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_ACCESS_TOKEN_EXPIRES_HOURS` - JWT token lifetime
- `VITE_API_URL` - Frontend API base URL
- `RABBITMQ_ORDER_QUEUE` - Default queue name for async jobs

### Secrets

Edit `configmap.yaml` Secret section (base64 encoded):

- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `JWT_SECRET_KEY` - JWT signing secret
- `GOOGLE_API_KEY` - Google Gemini API key
- `VITE_GOOGLE_CLIENT_ID` - Google OAuth client ID
- `RABBITMQ_URL` - RabbitMQ connection string for app and worker

To encode secrets:

```bash
echo -n "your-secret-value" | base64
```

## Access

### Application

- **NodePort**: Port 30001 on any cluster node
- **URL**: `http://<node-ip>:30001`

### PostgreSQL

- **NodePort**: Port 30434 on any cluster node
- **Connection**: `psql -h <node-ip> -p 30434 -U yeeter_user -d hl7_yeeter_db`

### Internal Services

- App: `yeeter-app.yeeter.svc.cluster.local:5001`
- Database: `postgres.yeeter.svc.cluster.local:5432`

## Persistent Storage

k3s uses `local-path` storage class by default:

- `postgres-data`: 5Gi for PostgreSQL data (`/var/lib/postgresql/data`)
- `yeeter-data`: 1Gi for uploads and simulation data (`/app/db-data`, `/app/uploads`)

Data persists across pod restarts.

## Health Checks

### Application Health

- **Liveness**: `GET /api/health` - checks if app is running
- **Readiness**: `GET /api/health` - checks if app is ready for traffic

### PostgreSQL Health

- **Liveness**: `pg_isready` command
- **Readiness**: `pg_isready` command

## Scaling

```bash
# Scale application replicas
kubectl scale deployment yeeter-app -n yeeter --replicas=3

# Note: PostgreSQL is stateful and should remain at 1 replica
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n yeeter
kubectl describe pod <pod-name> -n yeeter
```

### View logs

```bash
# Application logs
kubectl logs -f deployment/yeeter-app -n yeeter

# PostgreSQL logs
kubectl logs -f deployment/postgres -n yeeter
```

### Exec into containers

```bash
# App container
kubectl exec -it deployment/yeeter-app -n yeeter -- /bin/bash

# PostgreSQL container
kubectl exec -it deployment/postgres -n yeeter -- psql -U yeeter_user -d hl7_yeeter_db
```

### Check storage

```bash
kubectl get pvc -n yeeter
kubectl describe pvc postgres-data -n yeeter
```

### Image pull issues

If using a local image:

```bash
# Verify image is imported
sudo k3s crictl images | grep hl7-yeeter

# Re-import if needed
docker save hl7-yeeter:latest | sudo k3s ctr images import -
```

## Cleanup

```bash
# Delete entire deployment
kubectl delete namespace yeeter

# This will remove all resources (pods, services, pvcs)
# Note: PV data may persist depending on storage class reclaim policy
```

## Migration from Docker Compose

1. **Export database data** (if needed):

   ```bash
   docker exec yeeter_postgres pg_dump -U yeeter_user hl7_yeeter_db > backup.sql
   ```

2. **Stop Docker Compose**:

   ```bash
   docker compose down
   ```

3. **Deploy to k8s**:

   ```bash
   ./k8s/deploy.sh
   ```

4. **Import database data** (if needed):

   ```bash
   kubectl exec -i deployment/postgres -n yeeter -- psql -U yeeter_user -d hl7_yeeter_db < backup.sql
   ```

## Production Considerations

1. **Use a registry**: Push image to Docker registry instead of local import
2. **Set resource limits**: Adjust CPU/memory in deployment specs
3. **Use Ingress**: Add ingress controller for SSL/domain routing
4. **External database**: Consider managed PostgreSQL for production
5. **Secrets management**: Use external secrets operator or vault
6. **Monitoring**: Add Prometheus/Grafana for observability
7. **Backups**: Implement automated PVC snapshots or database backups
