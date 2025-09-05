# Container Registry Setup for Herd Controller

This guide shows how to deploy a container registry and use it with the herd-controller.

## Option 1: Deploy Registry with Ingress (Recommended)

### 1. Deploy the Registry

```bash
# Deploy registry with persistent storage and ingress
kubectl apply -f registry/registry-deployment.yaml

# Check deployment status
kubectl get pods -n registry
kubectl get pvc -n registry
kubectl get ingress -n registry
```

### 2. Configure DNS/Ingress

**Update the ingress hostname** in `registry/registry-deployment.yaml`:
```yaml
rules:
- host: registry.your-domain.com  # Change this
```

**Set up DNS** to point `registry.your-domain.com` to your ingress controller.

### 3. Test Registry Access

```bash
# Test registry is accessible
curl http://registry.your-domain.com/v2/

# Should return: {}
```

## Option 2: Deploy Registry with NodePort (Easier for Testing)

### 1. Deploy Registry + NodePort

```bash
# Deploy registry
kubectl apply -f registry/registry-deployment.yaml

# Add NodePort service
kubectl apply -f registry/registry-nodeport.yaml

# Get node IP and port
kubectl get nodes -o wide
kubectl get svc -n registry registry-nodeport
```

### 2. Test Access

```bash
# Test registry (replace NODE_IP with actual node IP)
curl http://NODE_IP:30500/v2/

# Should return: {}
```

## Build and Push Herd Controller Image

### 1. Build the Image with Podman

```bash
cd herd-crd

# Build the image
podman build -t herd-controller:latest .

# Tag for your registry
# Option A: Using ingress
podman tag herd-controller:latest registry.your-domain.com/herd-controller:latest

# Option B: Using NodePort (replace NODE_IP)
podman tag herd-controller:latest NODE_IP:30500/herd-controller:latest
```

### 2. Configure Podman for Insecure Registry (if not using TLS)

```bash
# Edit /etc/containers/registries.conf or ~/.config/containers/registries.conf
# Add your registry as insecure:

[[registry]]
location = "registry.your-domain.com"
insecure = true

# OR for NodePort:
[[registry]]
location = "NODE_IP:30500"
insecure = true
```

### 3. Push the Image

```bash
# Push to registry
# Option A: Using ingress
podman push registry.your-domain.com/herd-controller:latest

# Option B: Using NodePort
podman push NODE_IP:30500/herd-controller:latest

# Verify push worked
curl http://registry.your-domain.com/v2/herd-controller/tags/list
# Should show: {"name":"herd-controller","tags":["latest"]}
```

## Update Herd Controller to Use Your Registry

### Option 1: Update Helm Values

Edit `rancher-app/values.yaml`:

```yaml
controller:
  image:
    repository: registry.your-domain.com/herd-controller  # Your registry
    tag: latest
    pullPolicy: Always
```

Then install/upgrade:

```bash
helm upgrade --install herd-controller rancher-app/ \
  --namespace herd-system \
  --create-namespace \
  -f my-values.yaml
```

### Option 2: Update Kubernetes Manifests

Edit `manifests/controller/deployment.yaml`:

```yaml
containers:
- name: controller
  image: registry.your-domain.com/herd-controller:latest  # Your registry
  imagePullPolicy: Always
```

### Option 3: Override via Helm Command

```bash
helm install herd-controller rancher-app/ \
  --namespace herd-system \
  --create-namespace \
  --set controller.image.repository=registry.your-domain.com/herd-controller \
  --set controller.image.tag=latest \
  --set rancher.url="https://your-rancher.com" \
  --set rancher.token="token-xxxxx:..."
```

## Development Workflow

### 1. Build and Push Script

Create `scripts/build-and-push.sh`:

```bash
#!/bin/bash
set -e

REGISTRY="registry.your-domain.com"  # Change this
IMAGE_NAME="herd-controller"
TAG="${1:-latest}"

echo "Building ${IMAGE_NAME}:${TAG}..."
podman build -t ${IMAGE_NAME}:${TAG} .

echo "Tagging for registry..."
podman tag ${IMAGE_NAME}:${TAG} ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo "Pushing to registry..."
podman push ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo "✅ Image pushed: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
echo ""
echo "To update deployment:"
echo "kubectl set image -n herd-system deployment/herd-controller controller=${REGISTRY}/${IMAGE_NAME}:${TAG}"
```

Make it executable:
```bash
chmod +x scripts/build-and-push.sh
```

### 2. Update Makefile

Update `Makefile` to use your registry:

```makefile
# Variables
DOCKER_REGISTRY ?= registry.your-domain.com  # Change this
IMAGE_NAME ?= herd-controller
IMAGE_TAG ?= latest
FULL_IMAGE ?= $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build
build: ## Build the controller image with podman
	podman build -t $(FULL_IMAGE) .

.PHONY: push
push: build ## Push the controller image
	podman push $(FULL_IMAGE)

.PHONY: deploy-image
deploy-image: push ## Build, push and update deployment
	kubectl set image -n $(NAMESPACE) deployment/$(RELEASE_NAME) controller=$(FULL_IMAGE)
	kubectl rollout status -n $(NAMESPACE) deployment/$(RELEASE_NAME)
```

### 3. Development Cycle

```bash
# Make code changes...

# Build and push new image
make push

# Update running deployment
make deploy-image

# Or with specific tag
make push IMAGE_TAG=v0.1.1
kubectl set image -n herd-system deployment/herd-controller \
  controller=registry.your-domain.com/herd-controller:v0.1.1
```

## Troubleshooting

### Registry Issues

```bash
# Check registry logs
kubectl logs -n registry deployment/registry

# Check registry storage
kubectl exec -n registry deployment/registry -- ls -la /var/lib/registry

# Test registry API
curl http://registry.your-domain.com/v2/_catalog
```

### Image Pull Issues

```bash
# Check if image exists in registry
curl http://registry.your-domain.com/v2/herd-controller/tags/list

# Check pod events
kubectl describe pod -n herd-system -l app.kubernetes.io/name=herd

# Check if registry is accessible from cluster
kubectl run test-pod --image=curlimages/curl --rm -it --restart=Never -- \
  curl http://registry.registry.svc.cluster.local:5000/v2/
```

### Podman Issues

```bash
# Login to registry if needed
podman login registry.your-domain.com

# Check podman configuration
podman info

# Test registry connectivity
podman search registry.your-domain.com/
```

## Security Considerations

### 1. Enable TLS (Production)

For production, enable TLS:

```yaml
# Add to registry ConfigMap
http:
  tls:
    certificate: /etc/ssl/certs/registry.crt
    key: /etc/ssl/private/registry.key
```

### 2. Add Authentication

```yaml
# Add to registry ConfigMap
auth:
  htpasswd:
    realm: basic-realm
    path: /etc/registry/htpasswd
```

### 3. Image Pull Secrets

If using authentication:

```bash
# Create pull secret
kubectl create secret docker-registry registry-secret \
  --docker-server=registry.your-domain.com \
  --docker-username=your-user \
  --docker-password=your-password \
  --namespace=herd-system

# Add to deployment
spec:
  template:
    spec:
      imagePullSecrets:
      - name: registry-secret
```

## Registry Management

### List Images

```bash
# List all repositories
curl http://registry.your-domain.com/v2/_catalog

# List tags for specific image
curl http://registry.your-domain.com/v2/herd-controller/tags/list
```

### Clean Up Old Images

```bash
# Registry garbage collection (requires registry restart)
kubectl exec -n registry deployment/registry -- \
  registry garbage-collect /etc/docker/registry/config.yml

# Restart registry to free disk space
kubectl rollout restart -n registry deployment/registry
```

This setup gives you a complete container registry solution for your herd-controller development and deployment!
