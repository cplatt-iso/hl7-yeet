#!/bin/bash
# Deployment script for HL7 Yeeter on k3s
set -e

echo "=== HL7 Yeeter k8s Deployment ==="
echo ""

# Check if k3s is running
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: k3s cluster not accessible. Please ensure k3s is running."
    exit 1
fi

echo "✅ k3s cluster is accessible"
echo ""

# Build Docker image locally (k3s can use local images)
echo "Building hl7-yeeter:latest Docker image..."
docker build -t hl7-yeeter:latest .
if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi
echo "✅ Docker image built successfully"
echo ""

echo "Building hl7-yeeter-worker:latest Docker image..."
docker build -t hl7-yeeter-worker:latest -f Dockerfile.worker .
if [ $? -ne 0 ]; then
    echo "❌ Error: Worker Docker build failed"
    exit 1
fi
echo "✅ Worker Docker image built successfully"
echo ""

# Import image to k3s (k3s uses containerd, not docker)
echo "Importing image to k3s..."
docker save hl7-yeeter:latest | sudo k3s ctr images import -
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to import image to k3s"
    exit 1
fi
echo "✅ Image imported to k3s"
echo ""

echo "Importing worker image to k3s..."
docker save hl7-yeeter-worker:latest | sudo k3s ctr images import -
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to import worker image to k3s"
    exit 1
fi
echo "✅ Worker image imported to k3s"
echo ""

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/app.yaml
kubectl apply -f k8s/worker.yaml

echo ""
echo "✅ All manifests applied"
echo ""

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n yeeter --timeout=120s
echo "✅ PostgreSQL is ready"
echo ""

# Wait for app to be ready
echo "Waiting for application to be ready..."
kubectl wait --for=condition=ready pod -l app=yeeter-app -n yeeter --timeout=180s
echo "✅ Application is ready"
echo ""

echo "Waiting for worker to be ready..."
kubectl wait --for=condition=ready pod -l app=yeeter-worker -n yeeter --timeout=180s
echo "✅ Worker is ready"
echo ""

# Show deployment status
echo "=== Deployment Status ==="
kubectl get pods -n yeeter
echo ""
kubectl get svc -n yeeter
echo ""
kubectl get pvc -n yeeter
echo ""

# Get NodePort URLs
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
APP_PORT=$(kubectl get svc yeeter-app -n yeeter -o jsonpath='{.spec.ports[0].nodePort}')

POSTGRES_SVC_EXISTS=$(kubectl get svc postgres-external -n yeeter --no-headers --ignore-not-found)
if [ -n "$POSTGRES_SVC_EXISTS" ]; then
    DB_PORT=$(kubectl get svc postgres-external -n yeeter -o jsonpath='{.spec.ports[0].nodePort}')
else
    DB_PORT=""
fi

echo "=== Access Information ==="
echo "Application URL: http://${NODE_IP}:${APP_PORT}"
if [ -n "$DB_PORT" ]; then
    echo "PostgreSQL: ${NODE_IP}:${DB_PORT}"
else
    echo "PostgreSQL external service not configured"
fi
echo ""
echo "To view logs:"
echo "  kubectl logs -f deployment/yeeter-app -n yeeter"
echo "  kubectl logs -f deployment/postgres -n yeeter"
echo "  kubectl logs -f deployment/yeeter-worker -n yeeter"
echo ""
echo "To check pod status:"
echo "  kubectl get pods -n yeeter"
echo ""
echo "To delete deployment:"
echo "  kubectl delete namespace yeeter"
echo ""
echo "✅ Deployment complete!"
