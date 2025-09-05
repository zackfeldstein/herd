"""
Fleet client for deploying Helm charts via Fleet Bundles.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException

from .models import Chart, ChartDeployment, ChartDeploymentStatus, StackTargets

logger = logging.getLogger(__name__)


class FleetClient:
    """Client for managing Fleet Bundles to deploy Helm charts."""
    
    def __init__(self):
        """Initialize the Fleet client."""
        self.custom_api = k8s_client.CustomObjectsApi()
        # We'll determine the correct Fleet workspace based on the target cluster
    
    async def resolve_target_clusters(self, targets: StackTargets) -> List[str]:
        """Resolve target clusters based on the targets specification."""
        if targets.clusterIds:
            # Use explicit cluster IDs
            logger.info(f"Using explicit cluster IDs: {targets.clusterIds}")
            return targets.clusterIds
        
        elif targets.selector:
            # Use selector to find clusters
            try:
                # Check both Fleet workspaces for clusters
                all_clusters = []
                for workspace in ["fleet-default", "fleet-local"]:
                    try:
                        clusters = self.custom_api.list_namespaced_custom_object(
                            group="fleet.cattle.io",
                            version="v1alpha1", 
                            namespace=workspace,
                            plural="clusters"
                        )
                        all_clusters.extend(clusters.get("items", []))
                    except Exception:
                        continue
                
                matched_clusters = []
                for cluster in all_clusters:
                    cluster_labels = cluster.get("metadata", {}).get("labels", {})
                    if self._labels_match(cluster_labels, targets.selector.matchLabels):
                        matched_clusters.append(cluster["metadata"]["name"])
                
                logger.info(f"Found {len(matched_clusters)} clusters matching selector")
                return matched_clusters
                
            except ApiException as e:
                logger.error(f"Failed to list Fleet clusters: {e}")
                return []
        
        else:
            logger.warning("No cluster targets specified")
            return []
    
    def _labels_match(self, cluster_labels: Dict[str, str], selector_labels: Dict[str, str]) -> bool:
        """Check if cluster labels match the selector."""
        for key, value in selector_labels.items():
            if cluster_labels.get(key) != value:
                return False
        return True
    
    async def get_fleet_workspace_for_cluster(self, cluster_id: str) -> str:
        """Determine the correct Fleet workspace for a given cluster."""
        # Check both fleet workspaces to see where the cluster is registered
        for workspace in ["fleet-default", "fleet-local"]:
            try:
                registrations = self.custom_api.list_namespaced_custom_object(
                    group="fleet.cattle.io",
                    version="v1alpha1",
                    namespace=workspace,
                    plural="clusterregistrations"
                )
                
                for reg in registrations.get("items", []):
                    if reg.get("status", {}).get("clusterName") == cluster_id:
                        logger.info(f"Found cluster {cluster_id} in Fleet workspace {workspace}")
                        return workspace
                        
            except Exception as e:
                logger.debug(f"Could not check workspace {workspace}: {e}")
        
        # Default to fleet-local for local cluster, fleet-default for others
        if cluster_id == "local":
            return "fleet-local"
        else:
            return "fleet-default"

    async def create_or_update_bundle(
        self,
        chart: Chart,
        cluster_ids: List[str],
        merged_values: Dict[str, Any],
        stack_name: str,
        stack_namespace: str
    ) -> ChartDeployment:
        """Create or update a Fleet Bundle for the chart deployment."""
        
        bundle_name = f"{stack_name}-{chart.name}"
        start_time = datetime.utcnow().isoformat() + "Z"
        
        try:
            # Determine the correct Fleet workspace based on target clusters
            fleet_namespace = await self.get_fleet_workspace_for_cluster(cluster_ids[0])
            
            # Create Fleet Bundle specification
            bundle_spec = {
                "apiVersion": "fleet.cattle.io/v1alpha1",
                "kind": "Bundle",
                "metadata": {
                    "name": bundle_name,
                    "namespace": fleet_namespace,
                    "labels": {
                        "herd.suse.com/stack": stack_name,
                        "herd.suse.com/chart": chart.name,
                        "herd.suse.com/stack-namespace": stack_namespace
                    }
                },
                "spec": {
                    "defaultNamespace": chart.namespace,
                    "helm": {
                        "chart": chart.name,
                        "repo": chart.repo,
                        "version": chart.version,
                        "releaseName": chart.releaseName,
                        "values": merged_values,
                        "atomic": True,
                        "wait": chart.wait,
                        "timeout": chart.timeout,
                        "createNamespace": chart.createNamespace
                    },
                    "targets": self._create_targets_spec(cluster_ids)
                }
            }
            
            # Check if bundle already exists
            try:
                existing_bundle = self.custom_api.get_namespaced_custom_object(
                    group="fleet.cattle.io",
                    version="v1alpha1",
                    namespace=fleet_namespace,
                    plural="bundles",
                    name=bundle_name
                )
                
                # Update existing bundle
                logger.info(f"Updating existing Fleet Bundle {bundle_name} in {fleet_namespace}")
                self.custom_api.patch_namespaced_custom_object(
                    group="fleet.cattle.io",
                    version="v1alpha1",
                    namespace=fleet_namespace,
                    plural="bundles",
                    name=bundle_name,
                    body=bundle_spec
                )
                
            except ApiException as e:
                if e.status == 404:
                    # Create new bundle
                    logger.info(f"Creating new Fleet Bundle {bundle_name} in {fleet_namespace}")
                    self.custom_api.create_namespaced_custom_object(
                        group="fleet.cattle.io",
                        version="v1alpha1",
                        namespace=fleet_namespace,
                        plural="bundles",
                        body=bundle_spec
                    )
                else:
                    raise
            
            end_time = datetime.utcnow().isoformat() + "Z"
            
            # Return deployment status - Fleet will handle the actual deployment
            return ChartDeployment(
                chartName=chart.name,
                clusterId=",".join(cluster_ids),  # Multiple clusters
                releaseName=chart.releaseName,
                namespace=chart.namespace,
                version=chart.version,
                status=ChartDeploymentStatus.DEPLOYING,
                message=f"Fleet Bundle {bundle_name} created/updated successfully",
                lastUpdated=end_time
            )
            
        except Exception as e:
            logger.error(f"Failed to create/update Fleet Bundle {bundle_name}: {e}")
            return ChartDeployment(
                chartName=chart.name,
                clusterId=",".join(cluster_ids),
                releaseName=chart.releaseName,
                namespace=chart.namespace,
                version=chart.version,
                status=ChartDeploymentStatus.FAILED,
                message=f"Failed to create Fleet Bundle: {str(e)}",
                lastUpdated=datetime.utcnow().isoformat() + "Z"
            )
    
    def _create_targets_spec(self, cluster_ids: List[str]) -> List[Dict[str, Any]]:
        """Create Fleet targets specification for the given cluster IDs."""
        targets = []
        
        for cluster_id in cluster_ids:
            # Use the actual cluster ID as Fleet expects it
            targets.append({
                "clusterName": cluster_id
            })
        
        return targets
    
    async def delete_bundle(self, chart: Chart, stack_name: str, cluster_ids: List[str] = None) -> None:
        """Delete a Fleet Bundle."""
        bundle_name = f"{stack_name}-{chart.name}"
        
        # Try both Fleet workspaces to find and delete the bundle
        for workspace in ["fleet-default", "fleet-local"]:
            try:
                self.custom_api.delete_namespaced_custom_object(
                    group="fleet.cattle.io",
                    version="v1alpha1",
                    namespace=workspace,
                    plural="bundles",
                    name=bundle_name
                )
                logger.info(f"Deleted Fleet Bundle {bundle_name} from {workspace}")
                return
                
            except ApiException as e:
                if e.status == 404:
                    continue  # Try next workspace
                else:
                    logger.error(f"Failed to delete Fleet Bundle {bundle_name} from {workspace}: {e}")
        
        logger.info(f"Fleet Bundle {bundle_name} not found in any workspace")
    
    async def wait_for_bundle_ready(
        self,
        chart: Chart,
        stack_name: str,
        cluster_ids: List[str],
        timeout_seconds: int = 300
    ) -> bool:
        """Wait for a Fleet Bundle to become ready."""
        bundle_name = f"{stack_name}-{chart.name}"
        fleet_namespace = await self.get_fleet_workspace_for_cluster(cluster_ids[0])
        
        import asyncio
        
        for _ in range(timeout_seconds // 10):  # Check every 10 seconds
            try:
                bundle = self.custom_api.get_namespaced_custom_object(
                    group="fleet.cattle.io",
                    version="v1alpha1",
                    namespace=fleet_namespace,
                    plural="bundles",
                    name=bundle_name
                )
                
                conditions = bundle.get("status", {}).get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "Ready" and condition.get("status") == "True":
                        logger.info(f"Fleet Bundle {bundle_name} is ready")
                        return True
                
                await asyncio.sleep(10)
                
            except ApiException as e:
                logger.error(f"Failed to check Fleet Bundle status: {e}")
                return False
        
        logger.warning(f"Fleet Bundle {bundle_name} did not become ready within timeout")
        return False
