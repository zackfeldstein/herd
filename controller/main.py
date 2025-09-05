#!/usr/bin/env python3
"""
Herd Stack Controller - Kubernetes operator for managing Stack CRDs.
"""

import kopf
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .stack_manager import StackManager
from .models import StackSpec, StackStatus, ChartDeployment, DeploymentPhase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure the operator."""
    settings.posting.level = logging.INFO
    settings.watching.connect_timeout = 60
    settings.watching.server_timeout = 60
    logger.info("Herd Stack Controller starting up...")


@kopf.on.create('herd.suse.com', 'v1', 'stacks')
async def create_stack(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Stack creation."""
    logger.info(f"Creating stack: {namespace}/{name}")
    
    try:
        # Parse and validate the stack spec
        stack_spec = StackSpec(**spec)
        
        # Initialize stack manager
        stack_manager = StackManager()
        
        # Update status to Pending
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.PENDING,
            message="Stack creation started",
            target_clusters=[],
            deployments=[]
        )
        
        # Start deployment process
        await deploy_stack(stack_manager, stack_spec, name, namespace)
        
        return {"message": "Stack creation initiated"}
        
    except Exception as e:
        logger.error(f"Failed to create stack {namespace}/{name}: {e}")
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.FAILED,
            message=f"Stack creation failed: {str(e)}",
            target_clusters=[],
            deployments=[]
        )
        raise kopf.PermanentError(f"Stack creation failed: {e}")


@kopf.on.update('herd.suse.com', 'v1', 'stacks')
async def update_stack(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Stack updates."""
    logger.info(f"Updating stack: {namespace}/{name}")
    
    try:
        # Parse and validate the stack spec
        stack_spec = StackSpec(**spec)
        
        # Initialize stack manager
        stack_manager = StackManager()
        
        # Update status to Deploying
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.DEPLOYING,
            message="Stack update started",
            target_clusters=[],
            deployments=[]
        )
        
        # Start deployment process
        await deploy_stack(stack_manager, stack_spec, name, namespace)
        
        return {"message": "Stack update initiated"}
        
    except Exception as e:
        logger.error(f"Failed to update stack {namespace}/{name}: {e}")
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.FAILED,
            message=f"Stack update failed: {str(e)}",
            target_clusters=[],
            deployments=[]
        )
        raise kopf.PermanentError(f"Stack update failed: {e}")


@kopf.on.delete('herd.suse.com', 'v1', 'stacks')
async def delete_stack(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle Stack deletion."""
    logger.info(f"Deleting stack: {namespace}/{name}")
    
    try:
        # Parse the stack spec
        stack_spec = StackSpec(**spec)
        
        # Initialize stack manager
        stack_manager = StackManager()
        
        # Update status to Deleting
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.DELETING,
            message="Stack deletion started",
            target_clusters=[],
            deployments=[]
        )
        
        # Delete the stack
        await delete_stack_resources(stack_manager, stack_spec, name, namespace)
        
        logger.info(f"Stack {namespace}/{name} deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete stack {namespace}/{name}: {e}")
        # Don't raise error on deletion to avoid blocking finalizer
        logger.warning("Continuing with deletion despite errors")


async def deploy_stack(
    stack_manager: StackManager,
    stack_spec: StackSpec,
    name: str,
    namespace: str
):
    """Deploy a stack to target clusters."""
    try:
        # Resolve target clusters
        target_clusters = await stack_manager.resolve_target_clusters(stack_spec.targets)
        logger.info(f"Resolved target clusters for {namespace}/{name}: {target_clusters}")
        
        if not target_clusters:
            await update_stack_status(
                name=name,
                namespace=namespace,
                phase=DeploymentPhase.DEPLOYED,
                message="No target clusters found",
                target_clusters=[],
                deployments=[]
            )
            return
        
        # Update status with target clusters
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.DEPLOYING,
            message=f"Deploying to {len(target_clusters)} clusters",
            target_clusters=target_clusters,
            deployments=[]
        )
        
        # Deploy charts with dependency resolution
        all_deployments = []
        sorted_charts = stack_manager.sort_charts_by_dependencies(stack_spec.charts)
        
        for chart in sorted_charts:
            logger.info(f"Deploying chart {chart.name} for stack {namespace}/{name}")
            
            # Deploy chart to all target clusters
            chart_deployments = await stack_manager.deploy_chart_to_clusters(
                chart, target_clusters, stack_spec.env, namespace
            )
            
            all_deployments.extend(chart_deployments)
            
            # Update status with current deployments
            await update_stack_status(
                name=name,
                namespace=namespace,
                phase=DeploymentPhase.DEPLOYING,
                message=f"Deployed {chart.name} to {len(target_clusters)} clusters",
                target_clusters=target_clusters,
                deployments=all_deployments
            )
        
        # Check if all deployments succeeded
        failed_deployments = [d for d in all_deployments if d.status == "Failed"]
        
        if failed_deployments:
            await update_stack_status(
                name=name,
                namespace=namespace,
                phase=DeploymentPhase.FAILED,
                message=f"{len(failed_deployments)} chart deployments failed",
                target_clusters=target_clusters,
                deployments=all_deployments
            )
        else:
            await update_stack_status(
                name=name,
                namespace=namespace,
                phase=DeploymentPhase.DEPLOYED,
                message="All charts deployed successfully",
                target_clusters=target_clusters,
                deployments=all_deployments
            )
        
    except Exception as e:
        logger.error(f"Stack deployment failed: {e}")
        await update_stack_status(
            name=name,
            namespace=namespace,
            phase=DeploymentPhase.FAILED,
            message=f"Deployment failed: {str(e)}",
            target_clusters=[],
            deployments=[]
        )
        raise


async def delete_stack_resources(
    stack_manager: StackManager,
    stack_spec: StackSpec,
    name: str,
    namespace: str
):
    """Delete stack resources from target clusters."""
    try:
        # Resolve target clusters
        target_clusters = await stack_manager.resolve_target_clusters(stack_spec.targets)
        
        # Delete charts in reverse dependency order
        sorted_charts = stack_manager.sort_charts_by_dependencies(stack_spec.charts)
        sorted_charts.reverse()  # Delete in reverse order
        
        for chart in sorted_charts:
            logger.info(f"Deleting chart {chart.name} for stack {namespace}/{name}")
            
            # Delete chart from all target clusters
            await stack_manager.delete_chart_from_clusters(
                chart, target_clusters
            )
        
        logger.info(f"Stack {namespace}/{name} resources deleted")
        
    except Exception as e:
        logger.error(f"Failed to delete stack resources: {e}")
        raise


async def update_stack_status(
    name: str,
    namespace: str,
    phase: DeploymentPhase,
    message: str,
    target_clusters: List[str],
    deployments: List[ChartDeployment]
):
    """Update the status of a Stack resource."""
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
            "deployments": [d.dict() for d in deployments],
            "lastReconcileTime": datetime.utcnow().isoformat() + "Z",
            "observedGeneration": 1,
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if phase == DeploymentPhase.DEPLOYED else "False",
                    "reason": "DeploymentSucceeded" if phase == DeploymentPhase.DEPLOYED else "DeploymentInProgress",
                    "message": message,
                    "lastTransitionTime": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }
        
        # Update the Stack status
        api_client.patch_namespaced_custom_object_status(
            group="herd.suse.com",
            version="v1",
            namespace=namespace,
            plural="stacks",
            name=name,
            body={"status": status}
        )
        
        logger.info(f"Updated status for stack {namespace}/{name}: {phase.value}")
        
    except ApiException as e:
        logger.error(f"Failed to update stack status: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating stack status: {e}")


if __name__ == '__main__':
    kopf.run()
