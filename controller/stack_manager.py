"""
Stack manager for orchestrating chart deployments.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .models import Chart, ChartDeployment, ChartDeploymentStatus, StackTargets
from .rancher_client import RancherClient
from .values_merger import KubernetesValuesMerger

logger = logging.getLogger(__name__)


class StackManager:
    """Manages stack deployments across multiple clusters."""
    
    def __init__(self):
        """Initialize the stack manager."""
        self.rancher_client = RancherClient()
        self.values_merger = KubernetesValuesMerger()
    
    async def resolve_target_clusters(self, targets: StackTargets) -> List[str]:
        """Resolve target clusters based on the targets specification."""
        return await self.rancher_client.resolve_target_clusters(targets)
    
    def sort_charts_by_dependencies(self, charts: List[Chart]) -> List[Chart]:
        """Sort charts by their dependencies using topological sort."""
        # Create a map of chart names to charts
        chart_map = {chart.name: chart for chart in charts}
        
        # Track visited and recursion stack for cycle detection
        visited = set()
        rec_stack = set()
        sorted_charts = []
        
        def visit(chart_name: str):
            if chart_name in rec_stack:
                raise ValueError(f"Circular dependency detected involving {chart_name}")
            
            if chart_name in visited:
                return
            
            visited.add(chart_name)
            rec_stack.add(chart_name)
            
            chart = chart_map.get(chart_name)
            if chart and chart.dependsOn:
                for dep in chart.dependsOn:
                    if dep in chart_map:
                        visit(dep)
                    else:
                        logger.warning(f"Dependency '{dep}' not found for chart '{chart_name}'")
            
            rec_stack.remove(chart_name)
            if chart:
                sorted_charts.append(chart)
        
        # Visit all charts
        for chart in charts:
            if chart.name not in visited:
                visit(chart.name)
        
        return sorted_charts
    
    async def deploy_chart_to_clusters(
        self,
        chart: Chart,
        cluster_ids: List[str],
        env: str,
        namespace: str
    ) -> List[ChartDeployment]:
        """Deploy a single chart to multiple clusters."""
        deployments = []
        
        for cluster_id in cluster_ids:
            try:
                # Merge values for this cluster
                merged_values = await self.values_merger.merge_values(
                    chart.values, env, cluster_id, namespace
                )
                
                # Validate values
                warnings = self.values_merger.validate_values(merged_values)
                for warning in warnings:
                    logger.warning(f"Values warning for {chart.name} on {cluster_id}: {warning}")
                
                # Deploy the chart
                deployment = await self.rancher_client.create_or_update_app(
                    cluster_id, chart, merged_values
                )
                
                deployments.append(deployment)
                
                # Wait for deployment if requested
                if chart.wait and deployment.status == ChartDeploymentStatus.DEPLOYED:
                    timeout = self._parse_timeout(chart.timeout)
                    success = await self.rancher_client.wait_for_app_ready(
                        cluster_id, chart.namespace, chart.releaseName, timeout
                    )
                    if not success:
                        deployment.status = ChartDeploymentStatus.FAILED
                        deployment.message = "Deployment did not become ready within timeout"
                
            except Exception as e:
                logger.error(f"Failed to deploy {chart.name} to cluster {cluster_id}: {e}")
                deployment = ChartDeployment(
                    chartName=chart.name,
                    clusterId=cluster_id,
                    releaseName=chart.releaseName,
                    namespace=chart.namespace,
                    version=chart.version,
                    status=ChartDeploymentStatus.FAILED,
                    message=str(e),
                    lastUpdated=datetime.utcnow().isoformat() + "Z"
                )
                deployments.append(deployment)
        
        return deployments
    
    async def delete_chart_from_clusters(
        self,
        chart: Chart,
        cluster_ids: List[str]
    ) -> None:
        """Delete a chart from multiple clusters."""
        for cluster_id in cluster_ids:
            try:
                await self.rancher_client.delete_app(
                    cluster_id, chart.namespace, chart.releaseName
                )
                logger.info(f"Deleted {chart.name} from cluster {cluster_id}")
            except Exception as e:
                logger.error(f"Failed to delete {chart.name} from cluster {cluster_id}: {e}")
    
    def _parse_timeout(self, timeout_str: str) -> int:
        """Parse timeout string to seconds."""
        if not timeout_str:
            return 600  # Default 10 minutes
        
        timeout_str = timeout_str.lower().strip()
        
        if timeout_str.endswith('s'):
            return int(timeout_str[:-1])
        elif timeout_str.endswith('m'):
            return int(timeout_str[:-1]) * 60
        elif timeout_str.endswith('h'):
            return int(timeout_str[:-1]) * 3600
        else:
            try:
                return int(timeout_str)  # Assume seconds if no unit
            except ValueError:
                logger.warning(f"Invalid timeout format: {timeout_str}, using default 600s")
                return 600
