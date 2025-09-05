# Herd CRD Controller

**Kubernetes-native version of Herd Stack Controller**

This is a Kubernetes Custom Resource Definition (CRD) and Controller implementation of the Herd stack controller. Instead of using a CLI tool, users define `Stack` resources in Kubernetes and a controller running in the cluster handles the deployment to Rancher-managed clusters.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ kubectl apply   │───▶│  Stack CRD       │───▶│ Herd Controller │
│ -f stack.yaml   │    │  (K8s Resource)  │    │ (Running in K8s)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Stack Status     │    │ Rancher API     │
                       │ (Reconciliation) │    │ (Apps v2)       │
                       └──────────────────┘    └─────────────────┘
```

## Key Benefits

- **Kubernetes Native**: Use `kubectl` instead of custom CLI
- **GitOps Ready**: Stack definitions in Git, managed by ArgoCD/Flux
- **Rancher Integrated**: Runs as Rancher extension/app
- **Declarative**: True Kubernetes reconciliation loops
- **RBAC**: Native Kubernetes permissions on Stack resources
- **Observable**: Kubernetes events, status conditions, metrics

## Quick Start

### 1. Install the CRD and Controller

```bash
# Install CRDs
kubectl apply -f manifests/crds/

# Install controller
kubectl apply -f manifests/controller/
```

### 2. Create a Stack Resource

```bash
kubectl apply -f examples/rag-inference-stack.yaml
```

### 3. Monitor the Stack

```bash
# Watch stack status
kubectl get stacks -w

# Describe stack details
kubectl describe stack rag-inference

# View controller logs
kubectl logs -n herd-system deployment/herd-controller
```

## Usage Examples

### RAG Inference Stack

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: rag-inference
  namespace: default
spec:
  env: prod
  targets:
    selector:
      matchLabels:
        env: prod
        workload: ai-ml
  charts:
    - name: gpu-operator
      repo: https://helm.ngc.nvidia.com/nvidia
      version: "23.9.1"
      namespace: gpu-operator
      releaseName: gpu-operator
      values:
        configMapRefs:
          - name: gpu-operator-values
        inline:
          driver:
            enabled: true
      wait: true
      timeout: "15m"
    
    - name: qdrant
      repo: https://qdrant.github.io/qdrant-helm
      version: "0.7.4"
      namespace: vector-db
      releaseName: qdrant
      values:
        inline:
          persistence:
            size: "100Gi"
      dependsOn:
        - gpu-operator
      wait: true
```

### Check Stack Status

```bash
kubectl get stack rag-inference -o yaml
```

The controller updates the status with deployment progress:

```yaml
status:
  phase: "Deployed" # Pending, Deploying, Deployed, Failed
  conditions:
    - type: "Ready"
      status: "True"
      reason: "DeploymentSucceeded"
  deployments:
    - chartName: gpu-operator
      clusterId: c-m-gpu01
      status: "Deployed"
      lastUpdated: "2024-01-15T10:30:00Z"
```

## Development

### Build and Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run controller locally (against current kubectl context)
python controller/main.py

# Or build and run in Docker
docker build -t herd-controller .
docker run -v ~/.kube:/root/.kube herd-controller
```

### Testing

```bash
# Create test stack
kubectl apply -f examples/test-stack.yaml

# Check events
kubectl get events --field-selector involvedObject.kind=Stack

# Cleanup
kubectl delete -f examples/test-stack.yaml
```
