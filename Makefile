# Herd CRD Controller Makefile

# Variables
DOCKER_REGISTRY ?= docker.io
IMAGE_NAME ?= herd-controller
IMAGE_TAG ?= latest
FULL_IMAGE ?= $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

NAMESPACE ?= herd-system
RELEASE_NAME ?= herd-controller

# Build targets
.PHONY: build
build: ## Build the controller Docker image
	docker build -t $(FULL_IMAGE) .

.PHONY: push
push: build ## Push the controller Docker image
	docker push $(FULL_IMAGE)

# Development targets
.PHONY: dev-install
dev-install: ## Install dependencies for local development
	pip install -r requirements.txt

.PHONY: dev-run
dev-run: ## Run the controller locally (requires kubectl context)
	PYTHONPATH=. python controller/main.py

# Kubernetes targets
.PHONY: install-crds
install-crds: ## Install the Stack CRDs
	kubectl apply -f manifests/crds/

.PHONY: uninstall-crds
uninstall-crds: ## Uninstall the Stack CRDs
	kubectl delete -f manifests/crds/

.PHONY: install-manifests
install-manifests: install-crds ## Install controller via raw Kubernetes manifests
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f manifests/controller/

.PHONY: uninstall-manifests
uninstall-manifests: ## Uninstall controller via raw Kubernetes manifests
	kubectl delete -f manifests/controller/
	kubectl delete namespace $(NAMESPACE)

# Helm targets
.PHONY: helm-package
helm-package: ## Package the Helm chart
	cd rancher-app && helm package .

.PHONY: helm-install
helm-install: ## Install via Helm (requires values file)
	@if [ ! -f "my-values.yaml" ]; then \
		echo "Error: my-values.yaml not found. Copy and edit values.yaml first."; \
		exit 1; \
	fi
	helm upgrade --install $(RELEASE_NAME) rancher-app/ \
		--namespace $(NAMESPACE) \
		--create-namespace \
		-f my-values.yaml

.PHONY: helm-uninstall
helm-uninstall: ## Uninstall via Helm
	helm uninstall $(RELEASE_NAME) -n $(NAMESPACE)

# Testing targets
.PHONY: test-examples
test-examples: ## Apply example Stack resources
	kubectl apply -f examples/values-configmaps.yaml
	kubectl apply -f examples/secrets.yaml
	@echo "ConfigMaps and Secrets created. Now you can apply stack examples:"
	@echo "  kubectl apply -f examples/rag-inference-stack.yaml"
	@echo "  kubectl apply -f examples/ml-platform-stack.yaml"

.PHONY: clean-examples
clean-examples: ## Clean up example resources
	kubectl delete -f examples/ --ignore-not-found=true

.PHONY: logs
logs: ## View controller logs
	kubectl logs -n $(NAMESPACE) deployment/$(RELEASE_NAME) -f

.PHONY: status
status: ## Check controller and stack status
	@echo "=== Controller Status ==="
	kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "=== Stack Resources ==="
	kubectl get stacks -A
	@echo ""
	@echo "=== Recent Events ==="
	kubectl get events --field-selector involvedObject.kind=Stack --sort-by='.lastTimestamp' | tail -10

# Utility targets
.PHONY: validate-yaml
validate-yaml: ## Validate all YAML files
	@echo "Validating YAML files..."
	@find . -name "*.yaml" -o -name "*.yml" | xargs -I {} sh -c 'echo "Checking {}..." && python -c "import yaml; yaml.safe_load(open(\"{}\"))"'

.PHONY: check-rancher
check-rancher: ## Check Rancher connectivity (requires RANCHER_URL and RANCHER_TOKEN)
	@if [ -z "$(RANCHER_URL)" ] || [ -z "$(RANCHER_TOKEN)" ]; then \
		echo "Error: RANCHER_URL and RANCHER_TOKEN environment variables required"; \
		exit 1; \
	fi
	@echo "Testing Rancher connectivity..."
	@curl -k -H "Authorization: Bearer $(RANCHER_TOKEN)" "$(RANCHER_URL)/v3/clusters" | jq '.data[] | {id: .id, name: .name, state: .state}'

.PHONY: help
help: ## Show this help message
	@echo "Herd CRD Controller - Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Default target
.DEFAULT_GOAL := help
