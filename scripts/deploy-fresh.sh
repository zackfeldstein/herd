#!/bin/bash
set -e

# Configuration
REGISTRY="localhost:30500"
IMAGE_NAME="herd-controller"
TAG="${1:-v$(date +%s)}"  # Use timestamp if no tag provided

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🗑️  Cleaning up existing deployment...${NC}"
# 1. Delete the correct deployment
kubectl delete deployment -n herd-system herd-controller-herd-stack-controller || true

echo -e "${YELLOW}🧹 Cleaning up cached images...${NC}"
# 2. Clean up cached images with crictl (better for RKE2)
sudo /var/lib/rancher/rke2/bin/crictl \
  --runtime-endpoint unix:///run/k3s/containerd/containerd.sock \
  --image-endpoint unix:///run/k3s/containerd/containerd.sock \
  rmi docker.io/library/herd-controller:latest 2>/dev/null || true

sudo /var/lib/rancher/rke2/bin/crictl \
  --runtime-endpoint unix:///run/k3s/containerd/containerd.sock \
  --image-endpoint unix:///run/k3s/containerd/containerd.sock \
  rmi docker.io/library/herd-controller:v0.1.0 2>/dev/null || true

# Remove any other herd-controller images
sudo /var/lib/rancher/rke2/bin/crictl \
  --runtime-endpoint unix:///run/k3s/containerd/containerd.sock \
  --image-endpoint unix:///run/k3s/containerd/containerd.sock \
  images | grep herd-controller | awk '{print $1":"$2}' | xargs -r sudo /var/lib/rancher/rke2/bin/crictl \
  --runtime-endpoint unix:///run/k3s/containerd/containerd.sock \
  --image-endpoint unix:///run/k3s/containerd/containerd.sock \
  rmi 2>/dev/null || true

echo -e "${YELLOW}🏷️  Tagging image with: ${TAG}${NC}"
# 3. Tag and push fresh image
podman tag localhost/herd-controller:latest ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo -e "${YELLOW}📤 Pushing to registry...${NC}"
podman push ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo -e "${YELLOW}🚀 Installing with Helm...${NC}"
# 4. Reinstall with fresh tag
helm install herd-controller . \
  --namespace herd-system \
  --create-namespace \
  -f myvalues.yaml \
  --set controller.image.tag=${TAG}

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${YELLOW}Monitor with:${NC}"
echo "kubectl get pods -n herd-system -w"
echo "kubectl logs -n herd-system deployment/herd-controller-herd-stack-controller -f"
