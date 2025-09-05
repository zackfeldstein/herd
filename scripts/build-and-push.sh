#!/bin/bash
set -e

# Configuration - CHANGE THESE VALUES
REGISTRY="registry.your-domain.com"  # Change to your registry
IMAGE_NAME="herd-controller"
TAG="${1:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔨 Building ${IMAGE_NAME}:${TAG}...${NC}"
podman build -t ${IMAGE_NAME}:${TAG} .

echo -e "${YELLOW}🏷️  Tagging for registry...${NC}"
podman tag ${IMAGE_NAME}:${TAG} ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo -e "${YELLOW}📤 Pushing to registry...${NC}"
podman push ${REGISTRY}/${IMAGE_NAME}:${TAG}

echo -e "${GREEN}✅ Image pushed: ${REGISTRY}/${IMAGE_NAME}:${TAG}${NC}"
echo ""
echo -e "${YELLOW}To update running deployment:${NC}"
echo "kubectl set image -n herd-system deployment/herd-controller controller=${REGISTRY}/${IMAGE_NAME}:${TAG}"
echo ""
echo -e "${YELLOW}To verify image in registry:${NC}"
echo "curl http://${REGISTRY}/v2/${IMAGE_NAME}/tags/list"
