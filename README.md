# Herd CRD Controller

**Rancher-Native AI Orchestration Platform**

> **🏢 Enterprise Rancher Product**: Herd is an official **SUSE Rancher product** that extends your Rancher environment with AI-first orchestration capabilities.

Herd provides Kubernetes-native orchestration specifically designed for deploying, managing, and scaling AI/ML workloads across multiple Rancher-managed clusters. Built as a Custom Resource Definition (CRD) and Controller, Herd leverages **Rancher's Fleet** as its deployment engine to transform complex AI infrastructure deployments into simple, declarative Stack definitions that seamlessly deploy across your entire Rancher cluster fleet.

### **Powered by Rancher Fleet**
Herd uses **Rancher Fleet** under the hood to ensure reliable, secure, and scalable AI workload deployment across your multi-cluster Rancher environment. Every Stack deployment becomes a set of Fleet Bundles that leverage Fleet's proven GitOps capabilities, automatic retry mechanisms, and enterprise-grade security model.

## Why Herd for AI Workloads?

**Simplified AI Deployment**: Deploy complex AI stacks (LLMs, vector databases, GPU operators, inference engines) with a single YAML definition. No more managing dozens of Helm charts, dependencies, and cluster-specific configurations manually.

**Rancher Fleet-Powered Multi-Cluster**: Leverages Rancher's proven Fleet technology to seamlessly deploy and manage AI workloads across all your Rancher-managed clusters. Scale your AI infrastructure from single-node development to enterprise multi-cluster production environments with Rancher's battle-tested orchestration.

**Built-in AI Security**: Integrated NeuVector scanning ensures your AI containers are secure from vulnerabilities, with automated compliance checking for production AI deployments.

**AI-Specific Observability**: Purpose-built integration with SUSE observability stack provides deep insights into GPU utilization, model performance, inference latency, and resource consumption across your AI infrastructure.

**Enterprise Rancher Integration**: Deep integration with Rancher ecosystem including Fleet for GitOps workflows, Rancher cluster management, and native RBAC for secure multi-tenant AI environments.

## Architecture

Herd integrates deeply with the Rancher ecosystem, using Fleet as the deployment engine:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ kubectl apply   │───▶│  Stack CRD       │───▶│ Herd Controller │
│ -f stack.yaml   │    │  (K8s Resource)  │    │ (Rancher Native)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Stack Status     │    │ Rancher Fleet   │
                       │ (Reconciliation) │    │ (Multi-Cluster) │
                       └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                               ┌─────────────────────────────────────────┐
                               │          Rancher-Managed Clusters       │
                               │  ┌─────────────┐  ┌─────────────────┐   │
                               │  │ GPU Cluster │  │ CPU Cluster     │   │
                               │  │ (AI/ML)     │  │ (Standard)      │   │
                               │  └─────────────┘  └─────────────────┘   │
                               │  ┌─────────────┐  ┌─────────────────┐   │
                               │  │ Edge Cluster│  │ Dev Cluster     │   │
                               │  │ (IoT/Edge)  │  │ (Development)   │   │
                               │  └─────────────┘  └─────────────────┘   │
                               └─────────────────────────────────────────┘
```

### **How It Works**

1. **Define Stack**: Create a Stack CRD with cluster-specific AI configurations
2. **Herd Controller**: Processes Stack and creates Fleet Bundles with Helm charts
3. **Rancher Fleet**: Deploys Helm charts to target Rancher-managed clusters
4. **Multi-Cluster Deployment**: AI workloads automatically deployed across your fleet
5. **Status Reporting**: Real-time status aggregated from all clusters back to Stack CRD

## Rancher Fleet Integration

Herd is built on **Rancher Fleet**, the proven multi-cluster deployment technology that powers thousands of production Rancher environments. When you deploy a Stack:

### **Fleet Deployment Process**
1. **Stack Creation**: Herd Controller receives your Stack definition
2. **Fleet Bundle Generation**: Controller creates Fleet Bundles for each chart/cluster combination
3. **Fleet Distribution**: Rancher Fleet automatically distributes bundles to target clusters
4. **Helm Deployment**: Fleet agents on downstream clusters deploy Helm charts locally
5. **Status Aggregation**: Fleet reports deployment status back through Herd Controller

### **Why Fleet Matters for AI Workloads**
- **Proven at Scale**: Fleet manages deployments across thousands of clusters in production
- **Reliable Distribution**: Handles network partitions, cluster outages, and connectivity issues
- **GitOps Native**: Perfect for AI model deployment pipelines and infrastructure as code
- **Secure by Design**: Leverages Rancher's enterprise security model and cluster isolation
- **Bandwidth Efficient**: Optimized for large AI container images and model distributions

### **Fleet Workspace Management**
Herd automatically manages Fleet workspaces:
- **`fleet-default`**: For Rancher-managed downstream clusters
- **`fleet-local`**: For local management cluster deployments
- **Automatic Discovery**: Controller determines correct workspace based on cluster registration

## Key Benefits

- **Rancher Native**: Fully integrated Rancher product leveraging Fleet for multi-cluster deployment
- **Fleet-Powered**: Uses Rancher Fleet as the deployment engine for reliable, scalable workload distribution
- **Kubernetes Native**: Use `kubectl` instead of custom CLI, works with existing Rancher workflows
- **GitOps Ready**: Stack definitions in Git, managed by Rancher Fleet's proven GitOps capabilities
- **Multi-Cluster by Design**: Deploys across your entire Rancher-managed cluster fleet with cluster-specific configurations
- **Declarative**: True Kubernetes reconciliation loops with Fleet's robust deployment guarantees
- **Rancher RBAC**: Leverages Rancher's native RBAC and cluster management permissions
- **Fleet Observability**: Built on Fleet's proven observability with Kubernetes events, status conditions, and metrics
- **AI-First**: Purpose-built for deploying and orchestrating AI/ML workloads across Rancher environments
- **Security Integrated**: Built-in NeuVector scanning for container security across all managed clusters
- **SUSE Ecosystem**: Native integration with SUSE observability stack and Rancher's enterprise features

## Prerequisites

Herd requires a **Rancher-managed Kubernetes environment** with Fleet enabled:

- **Rancher Management Server**: Version 2.7+ with Fleet enabled
- **Downstream Clusters**: Registered with Rancher and Fleet agents running
- **Fleet Workspaces**: Configured for target cluster management
- **RBAC Permissions**: Rancher user with cluster management access

> **Note**: Herd is designed specifically for Rancher environments. It leverages Rancher's cluster management, Fleet's multi-cluster deployment capabilities, and integrates with the broader SUSE/Rancher ecosystem.

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

# Monitor Fleet deployment status
kubectl get bundles -A
kubectl get clusters.fleet.cattle.io -A

# Describe stack details
kubectl describe stack rag-inference

# View Herd controller logs
kubectl logs -n herd-system deployment/herd-controller

# View Fleet controller logs (for deployment troubleshooting)
kubectl logs -n cattle-fleet-system deployment/fleet-controller
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

**Rancher-Native AI Platform**: Built specifically for Rancher environments, Herd leverages your existing Rancher investment to bring enterprise-grade AI orchestration to your multi-cluster fleet. No additional infrastructure or learning curve required.

**Fleet-Powered Reliability**: Harness the proven power of Rancher Fleet for AI deployments. Transform complex multi-step AI deployments from hours of manual work to a single `kubectl apply` that reliably deploys across your entire Rancher-managed fleet.

**Enterprise AI Security**: Built-in NeuVector integration leverages your existing SUSE security stack. Every AI container is automatically scanned for vulnerabilities across all Rancher-managed clusters. Unified security posture for your AI infrastructure.

**SUSE Ecosystem Integration**: Deep integration with SUSE observability stack provides AI-optimized insights into GPU utilization, model performance, and inference latency across your Rancher clusters. Purpose-built dashboards for AI workloads within your existing SUSE monitoring infrastructure.

**Rancher Multi-Cluster AI**: Deploy the same AI stack across development, staging, and production clusters using Rancher's proven multi-cluster management. Scale from single-node development to enterprise multi-cluster production seamlessly with Fleet's reliable distribution.

**Enterprise Rancher Governance**: Leverages Rancher's native RBAC, cluster management, and GitOps workflows. Your AI infrastructure inherits Rancher's enterprise-grade governance, compliance, and operational excellence.

## Fleet-Based Troubleshooting

Since Herd uses Rancher Fleet for deployment, you can leverage Fleet's powerful troubleshooting capabilities:

### **Monitor Fleet Deployments**
```bash
# Check Fleet bundle status
kubectl get bundles -A
NAME                     BUNDLEDEPLOYMENTS-READY   STATUS
simple-ollama-ollama     1/1                       
gpu-operator-bundle      3/3                       

# Check cluster connectivity
kubectl get clusters.fleet.cattle.io -A
NAMESPACE       NAME      BUNDLES-READY   LAST-SEEN              STATUS
fleet-default   c-gpu-01  2/2             2025-09-12T15:27:20Z   
fleet-default   c-cpu-01  1/1             2025-09-12T15:28:36Z   

# Check bundle deployments on specific clusters
kubectl get bundledeployments -A | grep simple-ollama
```

### **Diagnose Fleet Issues**
```bash
# Check Fleet agent connectivity
kubectl describe cluster.fleet.cattle.io <cluster-name> -n fleet-default

# View Fleet bundle details
kubectl describe bundle <stack-name>-<chart-name> -n fleet-default

# Check Fleet controller logs
kubectl logs -n cattle-fleet-system deployment/fleet-controller

# Check downstream cluster Fleet agent logs (if accessible)
kubectl logs -n cattle-fleet-system deployment/fleet-agent
```

### **Common Fleet Deployment Patterns**
- **Bundle per Chart**: Each Helm chart becomes a Fleet Bundle
- **Cluster-Specific Bundles**: Different clusters can receive different chart configurations
- **Automatic Retry**: Fleet automatically retries failed deployments
- **Drift Detection**: Fleet continuously monitors and corrects configuration drift

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
