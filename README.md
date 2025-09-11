# Herd CRD Controller

**AI-First Kubernetes Orchestration Platform**

Herd is a Kubernetes-native orchestration platform specifically designed for deploying, managing, and scaling AI/ML workloads across multiple clusters. Built as a Custom Resource Definition (CRD) and Controller, Herd transforms complex AI infrastructure deployments into simple, declarative Stack definitions.

## Why Herd for AI Workloads?

**Simplified AI Deployment**: Deploy complex AI stacks (LLMs, vector databases, GPU operators, inference engines) with a single YAML definition. No more managing dozens of Helm charts, dependencies, and cluster-specific configurations manually.

**Multi-Cluster AI Orchestration**: Seamlessly deploy and manage AI workloads across development, staging, and production clusters. Scale your AI infrastructure from single-node development to multi-cluster production environments.

**Built-in AI Security**: Integrated NeuVector scanning ensures your AI containers are secure from vulnerabilities, with automated compliance checking for production AI deployments.

**AI-Specific Observability**: Purpose-built integration with SUSE observability stack provides deep insights into GPU utilization, model performance, inference latency, and resource consumption across your AI infrastructure.

**Enterprise-Ready**: Native integration with Rancher for enterprise cluster management, GitOps workflows for AI model deployment pipelines, and RBAC for secure multi-tenant AI environments.

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
- **AI-First**: Purpose-built for deploying and orchestrating AI/ML workloads
- **Security Integrated**: Built-in NeuVector scanning for container security
- **Observability Ready**: Native SUSE observability stack integration

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

# List all stacks with details
kubectl get stacks
NAME              PHASE      CLUSTERS   CHARTS   AGE
rag-inference     Deployed   2          3        5m30s
ollama-simple     Deployed   1          1        2m15s
gpu-cluster       Deploying  3          2        1m45s

# Describe stack details
kubectl describe stack rag-inference

# View controller logs
kubectl logs -n herd-system deployment/herd-controller
```

## Advanced Features

### Security Integration with NeuVector

Enable automatic container security scanning by adding the `security: enabled` flag to your Stack:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: secure-ai-stack
  namespace: default
spec:
  env: prod
  security: enabled  # Enables NeuVector scanning
  targets:
    selector:
      matchLabels:
        env: prod
        workload: ai-ml
  charts:
    - name: ollama
      repo: https://otwld.github.io/ollama-helm/
      version: "0.59.0"
      namespace: ollama
      releaseName: ollama
      values:
        inline:
          replicaCount: 2
```

When `security: enabled` is set, the Herd controller automatically:
- Integrates with NeuVector for runtime security scanning
- Scans all container images in the deployed charts
- Provides vulnerability reports and compliance checking
- Enforces security policies across AI workloads

### Observability with SUSE Observability Stack

Enable comprehensive monitoring and observability with the `observability: enabled` flag:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: observable-ai-stack
  namespace: default
spec:
  env: prod
  observability: enabled  # Enables SUSE observability integration
  targets:
    clusterIds:
      - c-m-gpu01
      - c-m-gpu02
  charts:
    - name: gpu-operator
      repo: https://helm.ngc.nvidia.com/nvidia
      version: "23.9.1"
      namespace: gpu-operator
      releaseName: gpu-operator
    - name: ollama
      repo: https://otwld.github.io/ollama-helm/
      version: "0.59.0"
      namespace: ollama
      releaseName: ollama
```

When `observability: enabled` is set, the controller automatically:
- Configures SUSE observability stack integration
- Sets up metrics collection for AI/ML workloads
- Enables distributed tracing across components
- Provides dashboards for GPU utilization, model performance, and inference metrics
- Integrates with Prometheus, Grafana, and Jaeger

### Combined Security and Observability

For production AI deployments, combine both features:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: production-ai-platform
  namespace: default
spec:
  env: prod
  security: enabled      # NeuVector scanning
  observability: enabled # SUSE observability
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
    - name: qdrant
      repo: https://qdrant.github.io/qdrant-helm
      version: "0.7.4"
      namespace: vector-db
      releaseName: qdrant
    - name: ollama
      repo: https://otwld.github.io/ollama-helm/
      version: "0.59.0"
      namespace: ollama
      releaseName: ollama
```

## Real-World AI Stack Examples

### Complete RAG (Retrieval-Augmented Generation) Platform

Deploy a full RAG inference platform with GPU support, vector database, and LLM serving:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: rag-inference-platform
  namespace: default
spec:
  env: prod
  security: enabled      # NeuVector scanning for all AI components
  observability: enabled # Full observability stack
  targets:
    selector:
      matchLabels:
        env: prod
        workload: ai-ml
        gpu: "true"
  charts:
    # GPU Infrastructure
    - name: gpu-operator
      repo: https://helm.ngc.nvidia.com/nvidia
      version: "23.9.1"
      namespace: gpu-operator
      releaseName: gpu-operator
      values:
        inline:
          driver:
            enabled: true
          toolkit:
            enabled: true
      wait: true
      timeout: "15m"
    
    # Vector Database for Embeddings
    - name: qdrant
      repo: https://qdrant.github.io/qdrant-helm
      version: "0.7.4"
      namespace: vector-db
      releaseName: qdrant
      values:
        inline:
          persistence:
            size: "500Gi"
            storageClass: "fast-ssd"
          resources:
            requests:
              memory: "8Gi"
              cpu: "2"
            limits:
              memory: "16Gi"
              cpu: "4"
      dependsOn:
        - gpu-operator
      wait: true
    
    # LLM Inference Engine
    - name: ollama
      repo: https://otwld.github.io/ollama-helm/
      version: "0.59.0"
      namespace: llm-serving
      releaseName: ollama
      values:
        inline:
          replicaCount: 3
          resources:
            requests:
              nvidia.com/gpu: 1
              memory: "16Gi"
            limits:
              nvidia.com/gpu: 1
              memory: "32Gi"
          persistence:
            enabled: true
            size: "100Gi"
      dependsOn:
        - gpu-operator
        - qdrant
      wait: true
```

### Multi-Model AI Serving Platform

Deploy multiple AI models with load balancing and auto-scaling:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: multi-model-serving
  namespace: default
spec:
  env: prod
  security: enabled
  observability: enabled
  targets:
    clusterIds:
      - c-m-gpu-cluster-01
      - c-m-gpu-cluster-02
      - c-m-gpu-cluster-03
  charts:
    # Model Serving Infrastructure
    - name: kserve
      repo: https://kserve.github.io/charts
      version: "0.11.2"
      namespace: kserve-system
      releaseName: kserve
      wait: true
    
    # GPU Support
    - name: gpu-operator
      repo: https://helm.ngc.nvidia.com/nvidia
      version: "23.9.1"
      namespace: gpu-operator
      releaseName: gpu-operator
      wait: true
    
    # Model Registry
    - name: mlflow
      repo: https://community-charts.github.io/helm-charts
      version: "0.7.19"
      namespace: mlflow
      releaseName: mlflow
      dependsOn:
        - kserve
      wait: true
```

### Development AI Stack

Lightweight AI development environment:

```yaml
apiVersion: herd.suse.com/v1
kind: Stack
metadata:
  name: ai-dev-environment
  namespace: default
spec:
  env: dev
  security: enabled  # Even dev environments need security
  targets:
    clusterIds:
      - c-m-dev-cluster
  charts:
    # Jupyter for AI Development
    - name: jupyterhub
      repo: https://jupyterhub.github.io/helm-chart/
      version: "3.1.0"
      namespace: jupyter
      releaseName: jupyterhub
      values:
        inline:
          singleuser:
            image:
              name: "jupyter/tensorflow-notebook"
              tag: "latest"
            cpu:
              limit: 2
              guarantee: 1
            memory:
              limit: "8G"
              guarantee: "4G"
    
    # Lightweight LLM for Testing
    - name: ollama
      repo: https://otwld.github.io/ollama-helm/
      version: "0.59.0"
      namespace: ollama
      releaseName: ollama-dev
      values:
        inline:
          replicaCount: 1
          resources:
            requests:
              memory: "4Gi"
              cpu: "2"
            limits:
              memory: "8Gi"
              cpu: "4"
```

### Monitoring Your AI Stacks

Check the status of your deployed AI infrastructure:

```bash
# List all AI stacks
kubectl get stacks
NAME                     PHASE      CLUSTERS   CHARTS   AGE
rag-inference-platform   Deployed   3          3        15m
multi-model-serving      Deployed   3          3        10m
ai-dev-environment       Deployed   1          2        5m
ollama-simple           Deployed   1          1        2m

# Get detailed status with security and observability info
kubectl get stack rag-inference-platform -o yaml
```

The controller provides comprehensive status including security and observability integration:

```yaml
status:
  phase: "Deployed"
  message: "All components deployed with security scanning and observability enabled"
  security:
    neuVectorEnabled: true
    scanStatus: "Completed"
    vulnerabilities: 0
    criticalIssues: 0
  observability:
    suseObservabilityEnabled: true
    metricsCollected: true
    dashboardsAvailable: 3
    alertsConfigured: 5
  conditions:
    - type: "Ready"
      status: "True"
      reason: "DeploymentSucceeded"
    - type: "SecurityScanned"
      status: "True"
      reason: "NeuVectorScanCompleted"
    - type: "ObservabilityConfigured"
      status: "True"
      reason: "SUSEObservabilityActive"
  deployments:
    - chartName: gpu-operator
      clusterId: c-m-gpu-cluster-01
      status: "Deployed"
      securityScan: "Passed"
      lastUpdated: "2024-01-15T10:30:00Z"
    - chartName: qdrant
      clusterId: c-m-gpu-cluster-01
      status: "Deployed"
      securityScan: "Passed"
      observabilityMetrics: "Active"
      lastUpdated: "2024-01-15T10:32:00Z"
    - chartName: ollama
      clusterId: c-m-gpu-cluster-01
      status: "Deployed"
      securityScan: "Passed"
      observabilityMetrics: "Active"
      gpuUtilization: "75%"
      lastUpdated: "2024-01-15T10:35:00Z"
  targetClusters:
    - c-m-gpu-cluster-01
    - c-m-gpu-cluster-02
    - c-m-gpu-cluster-03
```

### Access Security and Observability Dashboards

When security and observability are enabled, you can access:

```bash
# View NeuVector security dashboard
kubectl get ingress -n neuvector
# Navigate to: https://neuvector.your-domain.com

# Access SUSE observability dashboards
kubectl get ingress -n observability
# Navigate to: https://grafana.your-domain.com

# Check AI-specific metrics
kubectl port-forward -n observability svc/grafana 3000:80
# Open: http://localhost:3000/d/ai-workloads
```

## Why Choose Herd for AI Infrastructure?

**From Complex to Simple**: Transform multi-step AI deployments from hours of manual work to a single `kubectl apply`. Deploy complete RAG platforms, multi-model serving infrastructure, or development environments with one YAML file.

**Production-Ready AI Security**: Built-in NeuVector integration means every AI container is automatically scanned for vulnerabilities. No more manual security audits or compliance headaches.

**AI-Optimized Observability**: Deep insights into GPU utilization, model performance, inference latency, and resource consumption. Purpose-built dashboards for AI workloads, not generic infrastructure monitoring.

**Multi-Cluster AI at Scale**: Deploy the same AI stack across development, staging, and production clusters with environment-specific configurations. Scale from single-node development to multi-cluster production seamlessly.

**Enterprise AI Governance**: Native Rancher integration, RBAC controls, and GitOps workflows ensure your AI infrastructure meets enterprise requirements while remaining developer-friendly.

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
