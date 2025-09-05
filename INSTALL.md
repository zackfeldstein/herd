# Herd CRD Controller Installation Guide

This guide walks you through installing and using the Kubernetes-native version of the Herd Stack Controller.

## Prerequisites

- Kubernetes cluster with kubectl access
- Rancher management server with API access
- Rancher API token with cluster management permissions

## Installation Options

### Option 1: Install via Rancher Apps & Marketplace (Recommended)

1. **Package the Helm chart**:
   ```bash
   cd herd-crd/rancher-app
   helm package .
   ```

2. **Install via Rancher UI**:
   - Go to Rancher → Apps & Marketplace
   - Upload the packaged chart
   - Configure Rancher URL and token
   - Install to `herd-system` namespace

### Option 2: Direct Helm Installation

1. **Configure values**:
   ```bash
   cd herd-crd/rancher-app
   cp values.yaml my-values.yaml
   ```

2. **Edit `my-values.yaml`**:
   ```yaml
   rancher:
     url: "https://your-rancher.example.com"
     token: "token-xxxxx:your-rancher-token"
   ```

3. **Install with Helm**:
   ```bash
   helm install herd-controller . \
     --namespace herd-system \
     --create-namespace \
     -f my-values.yaml
   ```

### Option 3: Manual Kubernetes Manifests

1. **Install CRDs**:
   ```bash
   kubectl apply -f manifests/crds/
   ```

2. **Configure Rancher credentials**:
   ```bash
   # Edit the secret in manifests/controller/config.yaml
   vim manifests/controller/config.yaml
   
   # Apply configuration
   kubectl apply -f manifests/controller/config.yaml
   ```

3. **Install controller**:
   ```bash
   kubectl apply -f manifests/controller/
   ```

## Verification

### Check Installation

```bash
# Verify CRD is installed
kubectl get crd stacks.herd.suse.com

# Check controller is running
kubectl get pods -n herd-system

# View controller logs
kubectl logs -n herd-system deployment/herd-controller
```

### Test with Example Stack

1. **Create example values ConfigMaps**:
   ```bash
   kubectl apply -f examples/values-configmaps.yaml
   ```

2. **Deploy a test stack**:
   ```bash
   kubectl apply -f examples/ml-platform-stack.yaml
   ```

3. **Monitor stack deployment**:
   ```bash
   # Watch stack status
   kubectl get stacks -w
   
   # Describe stack details
   kubectl describe stack ml-platform
   
   # Check events
   kubectl get events --field-selector involvedObject.kind=Stack
   ```

## Usage Examples

### Basic Stack Definition

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: my-stack
  namespace: default
spec:
  env: prod
  targets:
    clusterIds:
      - c-m-cluster1
      - c-m-cluster2
  charts:
    - name: nginx
      repo: https://charts.bitnami.com/bitnami
      version: "15.4.4"
      namespace: web
      releaseName: nginx
      values:
        inline:
          replicaCount: 3
```

### Stack with Values from ConfigMaps

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: complex-stack
spec:
  env: prod
  targets:
    selector:
      matchLabels:
        env: prod
        gpu: "true"
  charts:
    - name: gpu-operator
      repo: https://helm.ngc.nvidia.com/nvidia
      version: "23.9.1"
      namespace: gpu-operator
      releaseName: gpu-operator
      values:
        configMapRefs:
          - name: gpu-operator-values
        perClusterConfigMapRef:
          name: cluster-overrides
        inline:
          driver:
            enabled: true
```

### Stack with Dependencies

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: dependent-stack
spec:
  env: dev
  targets:
    clusterIds: ["c-m-dev01"]
  charts:
    - name: postgresql
      repo: https://charts.bitnami.com/bitnami
      version: "12.12.10"
      namespace: database
      releaseName: postgres
      wait: true
    
    - name: app
      repo: https://my-charts.example.com
      version: "1.0.0"
      namespace: app
      releaseName: myapp
      dependsOn:
        - postgresql
      wait: true
```

## Monitoring and Troubleshooting

### Check Stack Status

```bash
# List all stacks
kubectl get stacks

# Get detailed status
kubectl get stack my-stack -o yaml

# Watch for status changes
kubectl get stacks -w
```

### View Stack Events

```bash
# Stack-specific events
kubectl describe stack my-stack

# All Stack events
kubectl get events --field-selector involvedObject.kind=Stack

# Controller events
kubectl get events -n herd-system
```

### Controller Logs

```bash
# View controller logs
kubectl logs -n herd-system deployment/herd-controller -f

# Previous container logs (if crashed)
kubectl logs -n herd-system deployment/herd-controller --previous
```

### Debug Stack Deployments

```bash
# Check if target clusters are resolved
kubectl get stack my-stack -o jsonpath='{.status.targetClusters}'

# View individual chart deployment status
kubectl get stack my-stack -o jsonpath='{.status.deployments}' | jq

# Check Rancher connectivity from controller
kubectl exec -n herd-system deployment/herd-controller -- \
  curl -k -H "Authorization: Bearer $RANCHER_TOKEN" \
  "$RANCHER_URL/v3/clusters"
```

## Configuration

### Rancher Configuration

The controller requires these environment variables:

- `RANCHER_URL`: Rancher management server URL
- `RANCHER_TOKEN`: API token with cluster management permissions
- `RANCHER_VERIFY_SSL`: SSL verification (default: true)
- `RANCHER_TIMEOUT`: Request timeout in seconds (default: 30)

### Values Merging

Values are merged in this precedence order:

1. **ConfigMap references** (`values.configMapRefs[]`)
2. **Environment overlay** (auto-discovered ConfigMap `herd-env-{env}`)
3. **Per-cluster overrides** (`values.perClusterConfigMapRef` with `{cluster-id}.yaml` keys)
4. **Secret references** (`values.secretRefs[]`)
5. **Inline values** (`values.inline`) - highest precedence

### RBAC Requirements

The controller needs these permissions:

- `herd.suse.com/stacks`: full access
- `configmaps`, `secrets`: read access
- `events`: create/patch access
- Standard kopf operator permissions

## Cleanup

### Delete Stacks

```bash
# Delete specific stack
kubectl delete stack my-stack

# Delete all stacks
kubectl delete stacks --all
```

### Uninstall Controller

```bash
# Via Helm
helm uninstall herd-controller -n herd-system

# Via kubectl
kubectl delete -f manifests/controller/
kubectl delete -f manifests/crds/
kubectl delete namespace herd-system
```

## Advanced Usage

### GitOps Integration

Stack resources work perfectly with GitOps tools:

```bash
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-stacks
spec:
  source:
    repoURL: https://git.example.com/stacks
    path: production/
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Multi-Environment Deployments

Use different namespaces for different environments:

```bash
# Development stacks
kubectl apply -f stacks/ -n development

# Production stacks  
kubectl apply -f stacks/ -n production
```

### Custom Resource Validation

The CRD includes comprehensive validation. Invalid stacks will be rejected:

```bash
# This will fail validation
kubectl apply -f - <<EOF
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: invalid-stack
spec:
  env: prod
  # Missing required 'targets' and 'charts' fields
EOF
```
