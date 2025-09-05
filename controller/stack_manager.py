"""
Stack manager for orchestrating chart deployments.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .models import Chart, ChartDeployment, ChartDeploymentStatus, StackTargets
from .fleet_client import FleetClient
from .values_merger import KubernetesValuesMerger

logger = logging.getLogger(__name__)


class StackManager:
    """Manages stack deployments across multiple clusters."""
    
    def __init__(self):
        """Initialize the stack manager."""
        self.fleet_client = FleetClient()
        self.values_merger = KubernetesValuesMerger()
    
    async def resolve_target_clusters(self, targets: StackTargets) -> List[str]:
        """Resolve target clusters based on the targets specification."""
        return await self.fleet_client.resolve_target_clusters(targets)
    
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
        stack_name: str,
        stack_namespace: str
    ) -> List[ChartDeployment]:
        """Deploy a single chart to multiple clusters using Fleet."""
        try:
            # Merge values for the deployment
            merged_values = await self.values_merger.merge_values(
                chart.values, env, cluster_ids[0] if cluster_ids else "default", stack_namespace
            )
            
            # Validate values
            warnings = self.values_merger.validate_values(merged_values)
            for warning in warnings:
                logger.warning(f"Values warning for {chart.name}: {warning}")
            
            # Create Fleet Bundle for multi-cluster deployment
            deployment = await self.fleet_client.create_or_update_bundle(
                chart, cluster_ids, merged_values, stack_name, stack_namespace
            )
            
            # Wait for deployment if requested
            if chart.wait and deployment.status == ChartDeploymentStatus.DEPLOYING:
                timeout = self._parse_timeout(chart.timeout)
                success = await self.fleet_client.wait_for_bundle_ready(
                    chart, stack_name, cluster_ids, timeout
                )
                if success:
                    deployment.status = ChartDeploymentStatus.DEPLOYED
                    deployment.message = "Fleet Bundle deployed successfully"
                else:
                    deployment.status = ChartDeploymentStatus.FAILED
                    deployment.message = "Fleet Bundle did not become ready within timeout"
            
            return [deployment]
            
        except Exception as e:
            logger.error(f"Failed to deploy {chart.name} via Fleet: {e}")
            deployment = ChartDeployment(
                chartName=chart.name,
                clusterId=",".join(cluster_ids),
                releaseName=chart.releaseName,
                namespace=chart.namespace,
                version=chart.version,
                status=ChartDeploymentStatus.FAILED,
                message=str(e),
                lastUpdated=datetime.utcnow().isoformat() + "Z"
            )
            return [deployment]
    
    async def delete_chart_from_clusters(
        self,
        chart: Chart,
        stack_name: str
    ) -> None:
        """Delete a chart's Fleet Bundle."""
        try:
            await self.fleet_client.delete_bundle(chart, stack_name)
            logger.info(f"Deleted Fleet Bundle for {chart.name}")
        except Exception as e:
            logger.error(f"Failed to delete Fleet Bundle for {chart.name}: {e}")
    
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
