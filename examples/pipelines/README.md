# Pipeline Examples

This directory contains example Pipeline CRD definitions for the Herd controller.

## Overview

Pipelines in Herd provide a declarative way to orchestrate AI/ML workflows across multiple Rancher-managed clusters. Each pipeline consists of sequential steps that can include:

- **Ingestion**: Data ingestion and preprocessing
- **Vector Database**: Vector database setup and configuration  
- **LLM**: Large Language Model deployment and serving
- **Service**: Application services and API gateways

## Example Pipelines

### 1. Complete RAG Pipeline (`example-pipeline.yaml`)

A comprehensive Retrieval-Augmented Generation (RAG) pipeline with:

- **Data Ingestion**: File system data processing with chunking
- **Vector Database**: Qdrant setup with persistent storage
- **LLM Serving**: Ollama with GPU support for Llama2:13b
- **RAG Service**: FastAPI service connecting vector DB and LLM

**Features:**
- Security scanning enabled
- Observability monitoring enabled
- Dependency management between steps
- Resource limits and scaling configuration
- Ingress and TLS configuration

### 2. Simple LLM Pipeline (`simple-pipeline.yaml`)

A minimal LLM serving pipeline with:

- **LLM Deployment**: Ollama with Llama2:7b model
- **API Gateway**: Simple FastAPI service

**Features:**
- Minimal configuration for testing
- No security/observability overhead
- Quick deployment for development

## Pipeline Configuration

### Step Types

#### Ingestion Step
```yaml
- name: data-ingestion
  type: ingestion
  config:
    source:
      type: "file-system"
      path: "/data/documents"
    processing:
      chunkSize: 1000
      chunkOverlap: 200
```

#### Vector Database Step
```yaml
- name: vector-database
  type: vector-db
  config:
    provider: "qdrant"
    configuration:
      collection:
        name: "documents"
        vectorSize: 1536
```

#### LLM Step
```yaml
- name: llm-serving
  type: llm
  config:
    provider: "ollama"
    model: "llama2:13b"
    configuration:
      gpu:
        enabled: true
```

#### Service Step
```yaml
- name: rag-service
  type: service
  config:
    application:
      name: "rag-api"
      framework: "fastapi"
```

### Dependencies

Steps can depend on other steps using the `dependsOn` field:

```yaml
steps:
  - name: step1
    type: ingestion
    # ... config
  
  - name: step2
    type: vector-db
    dependsOn:
      - step1
    # ... config
```

### Security and Observability

Enable security scanning and observability monitoring:

```yaml
spec:
  security: true      # Enable NeuVector scanning
  observability: true # Enable SUSE observability stack
```

## Usage

### Deploy a Pipeline

```bash
# Apply the pipeline
kubectl apply -f examples/pipelines/example-pipeline.yaml

# Check pipeline status
kubectl get pipelines

# Watch pipeline execution
kubectl get pipelines -w

# Describe pipeline details
kubectl describe pipeline rag-pipeline
```

### Monitor Pipeline Execution

```bash
# View pipeline events
kubectl get events --field-selector involvedObject.kind=Pipeline

# Check step status
kubectl get pipeline rag-pipeline -o jsonpath='{.status.stepStatus}'

# View controller logs
kubectl logs -n herd-system deployment/herd-controller -f
```

### Clean Up

```bash
# Delete pipeline
kubectl delete pipeline rag-pipeline

# Or delete all pipelines
kubectl delete pipelines --all
```

## Customization

### Cluster Targeting

Target specific clusters:

```yaml
spec:
  targets:
    clusterIds:
      - c-m-gpu-cluster-01
      - c-m-gpu-cluster-02
```

### Environment Configuration

Use environment-specific settings:

```yaml
spec:
  env: prod  # dev, staging, prod
```

### Resource Limits

Configure resources for each step:

```yaml
config:
  resources:
    requests:
      memory: "4Gi"
      cpu: "2"
    limits:
      memory: "8Gi"
      cpu: "4"
      nvidia.com/gpu: 1
```

### Timeouts and Retries

Configure execution parameters:

```yaml
timeout: "15m"  # Step timeout
retries: 3      # Number of retries on failure
```

## Integration Points

The pipeline controller integrates with:

- **Rancher Fleet**: For multi-cluster deployment
- **NeuVector**: For security scanning (when enabled)
- **SUSE Observability**: For monitoring (when enabled)
- **Kubernetes**: For resource management and status reporting

## Development

To extend pipeline functionality:

1. **Add new step types** in `controller/models.py`
2. **Implement step execution** in `controller/pipeline_controller.py`
3. **Update CRD schema** in `manifests/crds/pipeline-crd.yaml`
4. **Add examples** in `examples/pipelines/`

## Troubleshooting

### Common Issues

1. **Pipeline stuck in Pending**: Check cluster connectivity
2. **Step failures**: Review step configuration and resources
3. **Dependency errors**: Verify step names in `dependsOn`
4. **Resource limits**: Ensure sufficient cluster resources

### Debug Commands

```bash
# Check pipeline status
kubectl get pipeline <name> -o yaml

# View step status
kubectl get pipeline <name> -o jsonpath='{.status.stepStatus[*].phase}'

# Check controller logs
kubectl logs -n herd-system deployment/herd-controller | grep pipeline

# Verify CRD installation
kubectl get crd pipelines.herd.suse.com
```
