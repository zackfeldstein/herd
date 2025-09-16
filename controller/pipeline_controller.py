"""
Pipeline controller for managing Pipeline CRDs.
"""

import kopf
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .models import (
    PipelineSpec, PipelineStatus, PipelineStep, StepStatus,
    PipelinePhase, StepPhase, StepType, Condition
)
from .fleet_client import FleetClient
from .values_merger import KubernetesValuesMerger

# Configure logging
logger = logging.getLogger(__name__)


class PipelineManager:
    """Manages pipeline executions across multiple clusters."""
    
    def __init__(self):
        """Initialize the pipeline manager."""
        self.fleet_client = FleetClient()
        self.values_merger = KubernetesValuesMerger()
    
    async def resolve_target_clusters(self, targets) -> List[str]:
        """Resolve target clusters for pipeline execution."""
        # For pipelines, we only support explicit cluster IDs
        return targets.clusterIds
    
    def sort_steps_by_dependencies(self, steps: List[PipelineStep]) -> List[PipelineStep]:
        """Sort pipeline steps by their dependencies using topological sort."""
        # Create a map of step names to steps
        step_map = {step.name: step for step in steps}
        
        # Track visited and recursion stack for cycle detection
        visited = set()
        rec_stack = set()
        sorted_steps = []
        
        def visit(step_name: str):
            if step_name in rec_stack:
                raise ValueError(f"Circular dependency detected involving {step_name}")
            
            if step_name in visited:
                return
            
            visited.add(step_name)
            rec_stack.add(step_name)
            
            step = step_map.get(step_name)
            if step and step.dependsOn:
                for dep in step.dependsOn:
                    if dep in step_map:
                        visit(dep)
                    else:
                        logger.warning(f"Dependency '{dep}' not found for step '{step_name}'")
            
            rec_stack.remove(step_name)
            if step:
                sorted_steps.append(step)
        
        # Visit all steps
        for step in steps:
            if step.name not in visited:
                visit(step.name)
        
        return sorted_steps
    
    async def execute_step(
        self,
        step: PipelineStep,
        cluster_ids: List[str],
        env: str,
        pipeline_name: str,
        pipeline_namespace: str,
        security_enabled: bool = False,
        observability_enabled: bool = False
    ) -> StepStatus:
        """Execute a single pipeline step."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Executing step {step.name} ({step.type}) for pipeline {pipeline_namespace}/{pipeline_name}")
            
            # TODO: Implement step-specific execution logic based on step type
            if step.type == StepType.INGESTION:
                await self._execute_ingestion_step(step, cluster_ids, env, pipeline_name, pipeline_namespace)
            elif step.type == StepType.VECTOR_DB:
                await self._execute_vector_db_step(step, cluster_ids, env, pipeline_name, pipeline_namespace)
            elif step.type == StepType.LLM:
                await self._execute_llm_step(step, cluster_ids, env, pipeline_name, pipeline_namespace)
            elif step.type == StepType.SERVICE:
                await self._execute_service_step(step, cluster_ids, env, pipeline_name, pipeline_namespace)
            else:
                raise ValueError(f"Unknown step type: {step.type}")
            
            # TODO: Integrate security scanning if enabled
            if security_enabled:
                await self._perform_security_scan(step, cluster_ids)
            
            # TODO: Integrate observability monitoring if enabled
            if observability_enabled:
                await self._setup_observability(step, cluster_ids)
            
            end_time = datetime.utcnow()
            execution_time = str(end_time - start_time)
            
            return StepStatus(
                stepName=step.name,
                stepType=step.type,
                phase=StepPhase.COMPLETED,
                message=f"Step {step.name} executed successfully",
                lastUpdated=end_time.isoformat() + "Z",
                retryCount=0,
                executionTime=execution_time
            )
            
        except Exception as e:
            logger.error(f"Failed to execute step {step.name}: {e}")
            end_time = datetime.utcnow()
            
            return StepStatus(
                stepName=step.name,
                stepType=step.type,
                phase=StepPhase.FAILED,
                message=f"Step execution failed: {str(e)}",
                lastUpdated=end_time.isoformat() + "Z",
                retryCount=0,
                executionTime=str(end_time - start_time)
            )
    
    async def _execute_ingestion_step(
        self,
        step: PipelineStep,
        cluster_ids: List[str],
        env: str,
        pipeline_name: str,
        pipeline_namespace: str
    ):
        """Execute an ingestion step."""
        logger.info(f"Executing ingestion step: {step.name}")
        
        # TODO: Implement ingestion step execution
        # This could involve:
        # - Deploying data ingestion services (Kafka, Fluentd, etc.)
        # - Setting up data connectors
        # - Configuring data sources
        # - Creating Fleet Bundles for ingestion components
        
        # Example placeholder implementation:
        config = step.config
        logger.info(f"Ingestion config: {config}")
        
        # Simulate step execution
        await asyncio.sleep(2)
        
        # TODO: Create Fleet Bundle for ingestion components
        # bundle_name = f"{pipeline_name}-{step.name}"
        # await self.fleet_client.create_or_update_bundle(...)
    
    async def _execute_vector_db_step(
        self,
        step: PipelineStep,
        cluster_ids: List[str],
        env: str,
        pipeline_name: str,
        pipeline_namespace: str
    ):
        """Execute a vector database step."""
        logger.info(f"Executing vector-db step: {step.name}")
        
        # TODO: Implement vector database step execution
        # This could involve:
        # - Deploying vector databases (Qdrant, Weaviate, Pinecone, etc.)
        # - Setting up vector indexing
        # - Configuring embedding models
        # - Creating Fleet Bundles for vector DB components
        
        config = step.config
        logger.info(f"Vector DB config: {config}")
        
        # Simulate step execution
        await asyncio.sleep(3)
    
    async def _execute_llm_step(
        self,
        step: PipelineStep,
        cluster_ids: List[str],
        env: str,
        pipeline_name: str,
        pipeline_namespace: str
    ):
        """Execute an LLM step."""
        logger.info(f"Executing LLM step: {step.name}")
        
        # TODO: Implement LLM step execution
        # This could involve:
        # - Deploying LLM serving infrastructure (Ollama, vLLM, etc.)
        # - Setting up model endpoints
        # - Configuring inference parameters
        # - Creating Fleet Bundles for LLM components
        
        config = step.config
        logger.info(f"LLM config: {config}")
        
        # Simulate step execution
        await asyncio.sleep(4)
    
    async def _execute_service_step(
        self,
        step: PipelineStep,
        cluster_ids: List[str],
        env: str,
        pipeline_name: str,
        pipeline_namespace: str
    ):
        """Execute a service step."""
        logger.info(f"Executing service step: {step.name}")
        
        # TODO: Implement service step execution
        # This could involve:
        # - Deploying application services
        # - Setting up API gateways
        # - Configuring load balancers
        # - Creating Fleet Bundles for service components
        
        config = step.config
        logger.info(f"Service config: {config}")
        
        # Simulate step execution
        await asyncio.sleep(2)
    
    async def _perform_security_scan(self, step: PipelineStep, cluster_ids: List[str]):
        """Perform security scanning for step components."""
        logger.info(f"Performing security scan for step {step.name}")
        
        # TODO: Integrate with NeuVector or other security scanning tools
        # This could involve:
        # - Scanning container images
        # - Checking for vulnerabilities
        # - Validating security policies
        # - Reporting security findings
        
        # Simulate security scan
        await asyncio.sleep(1)
        logger.info(f"Security scan completed for step {step.name}")
    
    async def _setup_observability(self, step: PipelineStep, cluster_ids: List[str]):
        """Setup observability monitoring for step."""
        logger.info(f"Setting up observability for step {step.name}")
        
        # TODO: Integrate with SUSE observability stack
        # This could involve:
        # - Configuring metrics collection
        # - Setting up distributed tracing
        # - Creating monitoring dashboards
        # - Configuring alerting rules
        
        # Simulate observability setup
        await asyncio.sleep(1)
        logger.info(f"Observability setup completed for step {step.name}")
    
    async def cleanup_step_resources(
        self,
        step: PipelineStep,
        pipeline_name: str,
        cluster_ids: List[str]
    ):
        """Clean up resources created by a pipeline step."""
        logger.info(f"Cleaning up resources for step {step.name}")
        
        # TODO: Implement step cleanup logic
        # This could involve:
        # - Deleting Fleet Bundles
        # - Removing deployed components
        # - Cleaning up persistent volumes
        # - Removing monitoring configurations
        
        # Simulate cleanup
        await asyncio.sleep(1)
        logger.info(f"Cleanup completed for step {step.name}")


@kopf.on.create('herd.suse.com', 'v1', 'pipelines')
async def create_pipeline(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Pipeline creation."""
    logger.info(f"Creating pipeline: {namespace}/{name}")
    
    try:
        # Parse and validate the pipeline spec
        pipeline_spec = PipelineSpec(**spec)
        
        # Initialize pipeline manager
        pipeline_manager = PipelineManager()
        
        # Update status to Pending
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.PENDING,
            message="Pipeline creation started",
            target_clusters=[],
            step_statuses=[]
        )
        
        # Start pipeline execution
        await execute_pipeline(pipeline_manager, pipeline_spec, name, namespace)
        
        return {"message": "Pipeline creation initiated"}
        
    except Exception as e:
        logger.error(f"Failed to create pipeline {namespace}/{name}: {e}")
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.FAILED,
            message=f"Pipeline creation failed: {str(e)}",
            target_clusters=[],
            step_statuses=[]
        )
        raise kopf.PermanentError(f"Pipeline creation failed: {e}")


@kopf.on.update('herd.suse.com', 'v1', 'pipelines')
async def update_pipeline(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Pipeline updates."""
    logger.info(f"Updating pipeline: {namespace}/{name}")
    
    try:
        # Parse and validate the pipeline spec
        pipeline_spec = PipelineSpec(**spec)
        
        # Initialize pipeline manager
        pipeline_manager = PipelineManager()
        
        # Update status to Running
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.RUNNING,
            message="Pipeline update started",
            target_clusters=[],
            step_statuses=[]
        )
        
        # Start pipeline execution
        await execute_pipeline(pipeline_manager, pipeline_spec, name, namespace)
        
        return {"message": "Pipeline update initiated"}
        
    except Exception as e:
        logger.error(f"Failed to update pipeline {namespace}/{name}: {e}")
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.FAILED,
            message=f"Pipeline update failed: {str(e)}",
            target_clusters=[],
            step_statuses=[]
        )
        raise kopf.PermanentError(f"Pipeline update failed: {e}")


@kopf.on.delete('herd.suse.com', 'v1', 'pipelines')
async def delete_pipeline(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Pipeline deletion."""
    logger.info(f"Deleting pipeline: {namespace}/{name}")
    
    try:
        # Parse the pipeline spec
        pipeline_spec = PipelineSpec(**spec)
        
        # Initialize pipeline manager
        pipeline_manager = PipelineManager()
        
        # Clean up pipeline resources
        await cleanup_pipeline_resources(pipeline_manager, pipeline_spec, name, namespace)
        
        logger.info(f"Pipeline {namespace}/{name} deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete pipeline {namespace}/{name}: {e}")
        # Don't raise error on deletion to avoid blocking finalizer
        logger.warning("Continuing with deletion despite errors")


async def execute_pipeline(
    pipeline_manager: PipelineManager,
    pipeline_spec: PipelineSpec,
    name: str,
    namespace: str
):
    """Execute a pipeline across target clusters."""
    try:
        # Resolve target clusters
        target_clusters = await pipeline_manager.resolve_target_clusters(pipeline_spec.targets)
        logger.info(f"Resolved target clusters for {namespace}/{name}: {target_clusters}")
        
        if not target_clusters:
            await update_pipeline_status(
                name=name,
                namespace=namespace,
                phase=PipelinePhase.COMPLETED,
                message="No target clusters found",
                target_clusters=[],
                step_statuses=[]
            )
            return
        
        # Update status with target clusters
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.RUNNING,
            message=f"Executing pipeline on {len(target_clusters)} clusters",
            target_clusters=target_clusters,
            step_statuses=[]
        )
        
        # Execute steps with dependency resolution
        all_step_statuses = []
        sorted_steps = pipeline_manager.sort_steps_by_dependencies(pipeline_spec.steps)
        
        for step in sorted_steps:
            logger.info(f"Executing step {step.name} for pipeline {namespace}/{name}")
            
            # Execute step on all target clusters
            step_status = await pipeline_manager.execute_step(
                step, target_clusters, pipeline_spec.env, name, namespace,
                pipeline_spec.security, pipeline_spec.observability
            )
            
            all_step_statuses.append(step_status)
            
            # Update status with current step statuses
            await update_pipeline_status(
                name=name,
                namespace=namespace,
                phase=PipelinePhase.RUNNING,
                message=f"Executed step {step.name}",
                target_clusters=target_clusters,
                step_statuses=all_step_statuses
            )
        
        # Check if all steps succeeded
        failed_steps = [s for s in all_step_statuses if s.phase == StepPhase.FAILED]
        
        if failed_steps:
            await update_pipeline_status(
                name=name,
                namespace=namespace,
                phase=PipelinePhase.FAILED,
                message=f"{len(failed_steps)} steps failed",
                target_clusters=target_clusters,
                step_statuses=all_step_statuses
            )
        else:
            await update_pipeline_status(
                name=name,
                namespace=namespace,
                phase=PipelinePhase.COMPLETED,
                message="All steps executed successfully",
                target_clusters=target_clusters,
                step_statuses=all_step_statuses
            )
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        await update_pipeline_status(
            name=name,
            namespace=namespace,
            phase=PipelinePhase.FAILED,
            message=f"Execution failed: {str(e)}",
            target_clusters=[],
            step_statuses=[]
        )
        raise


async def cleanup_pipeline_resources(
    pipeline_manager: PipelineManager,
    pipeline_spec: PipelineSpec,
    name: str,
    namespace: str
):
    """Clean up pipeline resources from target clusters."""
    try:
        # Resolve target clusters
        target_clusters = await pipeline_manager.resolve_target_clusters(pipeline_spec.targets)
        
        # Clean up steps in reverse dependency order
        sorted_steps = pipeline_manager.sort_steps_by_dependencies(pipeline_spec.steps)
        sorted_steps.reverse()  # Clean up in reverse order
        
        for step in sorted_steps:
            logger.info(f"Cleaning up step {step.name} for pipeline {namespace}/{name}")
            
            # Clean up step resources
            await pipeline_manager.cleanup_step_resources(step, name, target_clusters)
        
        logger.info(f"Pipeline {namespace}/{name} resources cleaned up")
        
    except Exception as e:
        logger.error(f"Failed to cleanup pipeline resources: {e}")
        raise


async def update_pipeline_status(
    name: str,
    namespace: str,
    phase: PipelinePhase,
    message: str,
    target_clusters: List[str],
    step_statuses: List[StepStatus]
):
    """Update the status of a Pipeline resource."""
    try:
        import kubernetes.client as k8s_client
        from kubernetes.client.rest import ApiException
        
        # Create API client
        api_client = k8s_client.CustomObjectsApi()
        
        # Prepare status update
        status = {
            "phase": phase.value,
            "message": message,
            "targetClusters": target_clusters,
            "stepStatus": [s.model_dump() for s in step_statuses],
            "lastReconcileTime": datetime.utcnow().isoformat() + "Z",
            "observedGeneration": 1,
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if phase == PipelinePhase.COMPLETED else "False",
                    "reason": "ExecutionSucceeded" if phase == PipelinePhase.COMPLETED else "ExecutionInProgress",
                    "message": message,
                    "lastTransitionTime": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }
        
        # Update the Pipeline status
        api_client.patch_namespaced_custom_object_status(
            group="herd.suse.com",
            version="v1",
            namespace=namespace,
            plural="pipelines",
            name=name,
            body={"status": status}
        )
        
        logger.info(f"Updated status for pipeline {namespace}/{name}: {phase.value}")
        
    except ApiException as e:
        logger.error(f"Failed to update pipeline status: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating pipeline status: {e}")
