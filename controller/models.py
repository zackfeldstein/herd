"""
Pydantic models for the Herd Stack Controller.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class DeploymentPhase(str, Enum):
    """Phases of stack deployment."""
    PENDING = "Pending"
    DEPLOYING = "Deploying"
    DEPLOYED = "Deployed"
    FAILED = "Failed"
    DELETING = "Deleting"


class ChartDeploymentStatus(str, Enum):
    """Status of individual chart deployments."""
    PENDING = "Pending"
    DEPLOYING = "Deploying"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


class TargetSelector(BaseModel):
    """Selector for targeting clusters based on labels."""
    matchLabels: Dict[str, str] = Field(..., description="Labels to match clusters against")


class StackTargets(BaseModel):
    """Target specification for clusters."""
    clusterIds: Optional[List[str]] = Field(None, description="Explicit list of cluster IDs")
    selector: Optional[TargetSelector] = Field(None, description="Selector to match clusters")


class ConfigMapRef(BaseModel):
    """Reference to a ConfigMap containing values."""
    name: str = Field(..., description="Name of the ConfigMap")
    namespace: Optional[str] = Field(None, description="Namespace of the ConfigMap")
    key: str = Field(default="values.yaml", description="Key in the ConfigMap")


class SecretRef(BaseModel):
    """Reference to a Secret containing values."""
    name: str = Field(..., description="Name of the Secret")
    namespace: Optional[str] = Field(None, description="Namespace of the Secret")
    key: str = Field(default="values.yaml", description="Key in the Secret")


class ChartValues(BaseModel):
    """Values configuration for a Helm chart."""
    configMapRefs: Optional[List[ConfigMapRef]] = Field(default_factory=list, description="References to ConfigMaps")
    secretRefs: Optional[List[SecretRef]] = Field(default_factory=list, description="References to Secrets")
    perClusterConfigMapRef: Optional[ConfigMapRef] = Field(None, description="ConfigMap with per-cluster overrides")
    inline: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Inline values")


class Chart(BaseModel):
    """Helm chart specification."""
    name: str = Field(..., description="Name of the Helm chart")
    repo: str = Field(..., description="Helm repository URL or name")
    version: str = Field(..., description="Chart version")
    namespace: str = Field(..., description="Target Kubernetes namespace")
    releaseName: str = Field(..., description="Helm release name")
    values: Optional[ChartValues] = Field(default_factory=ChartValues, description="Values configuration")
    dependsOn: Optional[List[str]] = Field(default_factory=list, description="List of charts this depends on")
    wait: Optional[bool] = Field(default=True, description="Wait for deployment to complete")
    timeout: Optional[str] = Field(default="10m", description="Timeout for deployment")
    createNamespace: Optional[bool] = Field(default=True, description="Create namespace if it doesn't exist")


class StackSpec(BaseModel):
    """Stack specification."""
    env: str = Field(..., description="Environment name (e.g., dev, staging, prod)")
    targets: StackTargets = Field(..., description="Target cluster specification")
    charts: List[Chart] = Field(..., description="List of charts to deploy")


class ChartDeployment(BaseModel):
    """Status of a chart deployment."""
    chartName: str
    clusterId: str
    releaseName: str
    namespace: str
    version: str
    status: ChartDeploymentStatus
    message: Optional[str] = None
    lastUpdated: str


class Condition(BaseModel):
    """Condition represents an observation of the Stack's state."""
    type: str
    status: str  # True, False, Unknown
    reason: Optional[str] = None
    message: Optional[str] = None
    lastTransitionTime: str


class StackStatus(BaseModel):
    """Status of a Stack resource."""
    phase: DeploymentPhase
    message: Optional[str] = None
    observedGeneration: Optional[int] = None
    conditions: List[Condition] = Field(default_factory=list)
    deployments: List[ChartDeployment] = Field(default_factory=list)
    targetClusters: List[str] = Field(default_factory=list)
    lastReconcileTime: Optional[str] = None


# Pipeline Models

class PipelinePhase(str, Enum):
    """Phases of pipeline execution."""
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class StepPhase(str, Enum):
    """Phases of individual step execution."""
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"


class StepType(str, Enum):
    """Types of pipeline steps."""
    INGESTION = "ingestion"
    VECTOR_DB = "vector-db"
    LLM = "llm"
    SERVICE = "service"


class PipelineTargets(BaseModel):
    """Target specification for pipeline clusters."""
    clusterIds: List[str] = Field(..., description="Explicit list of cluster IDs")


class PipelineStep(BaseModel):
    """Pipeline step specification."""
    name: str = Field(..., description="Name of the pipeline step")
    type: StepType = Field(..., description="Type of pipeline step")
    config: Dict[str, Any] = Field(..., description="Step-specific configuration parameters")
    dependsOn: Optional[List[str]] = Field(default_factory=list, description="List of steps this step depends on")
    timeout: Optional[str] = Field(default="10m", description="Timeout for step execution")
    retries: Optional[int] = Field(default=3, ge=0, le=10, description="Number of retries on failure")


class PipelineSpec(BaseModel):
    """Pipeline specification."""
    env: str = Field(..., description="Environment name (e.g., dev, staging, prod)")
    targets: PipelineTargets = Field(..., description="Target cluster specification")
    steps: List[PipelineStep] = Field(..., description="List of pipeline steps to execute")
    security: Optional[bool] = Field(default=False, description="Enable security scanning for pipeline components")
    observability: Optional[bool] = Field(default=False, description="Enable observability monitoring for pipeline")


class StepStatus(BaseModel):
    """Status of a pipeline step execution."""
    stepName: str
    stepType: StepType
    phase: StepPhase
    message: Optional[str] = None
    lastUpdated: str
    retryCount: Optional[int] = Field(default=0, description="Number of retries attempted")
    executionTime: Optional[str] = Field(None, description="Duration of step execution")


class PipelineStatus(BaseModel):
    """Status of a Pipeline resource."""
    phase: PipelinePhase
    message: Optional[str] = None
    observedGeneration: Optional[int] = None
    conditions: List[Condition] = Field(default_factory=list)
    stepStatus: List[StepStatus] = Field(default_factory=list)
    targetClusters: List[str] = Field(default_factory=list)
    lastReconcileTime: Optional[str] = None
