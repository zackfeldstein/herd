"""
Rancher API client for the Kubernetes controller.
"""

import os
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from .models import TargetSelector, Chart, ChartDeploymentStatus, ChartDeployment

logger = logging.getLogger(__name__)


class RancherAPIError(Exception):
    """Exception raised for Rancher API errors."""
    pass


class RancherClient:
    """Client for interacting with Rancher API from within the controller."""
    
    def __init__(self):
        """Initialize the Rancher client from environment variables."""
        self.rancher_url = os.getenv("RANCHER_URL")
        self.rancher_token = os.getenv("RANCHER_TOKEN") 
        self.verify_ssl = os.getenv("RANCHER_VERIFY_SSL", "true").lower() == "true"
        self.timeout = int(os.getenv("RANCHER_TIMEOUT", "30"))
        
        if not self.rancher_url or not self.rancher_token:
            raise ValueError("RANCHER_URL and RANCHER_TOKEN environment variables are required")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.rancher_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.session.verify = self.verify_ssl
        
        # Ensure URL ends with /v3 for Rancher API
        if not self.rancher_url.endswith('/v3'):
            if self.rancher_url.endswith('/'):
                self.base_url = f"{self.rancher_url}v3"
            else:
                self.base_url = f"{self.rancher_url}/v3"
        else:
            self.base_url = self.rancher_url
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Rancher API."""
        url = urljoin(self.base_url + "/", endpoint)
        
        try:
            response = self.session.request(
                method, url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Rancher API request failed: {e}")
            raise RancherAPIError(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise RancherAPIError(f"Invalid JSON response: {e}")
    
    async def get_clusters(self) -> List[Dict[str, Any]]:
        """Get all clusters from Rancher."""
        logger.info("Fetching clusters from Rancher")
        response = self._make_request("GET", "clusters")
        return response.get("data", [])
    
    async def resolve_target_clusters(self, targets) -> List[str]:
        """Resolve target clusters based on cluster IDs or selector."""
        if targets.clusterIds:
            logger.info(f"Using explicit cluster IDs: {targets.clusterIds}")
            return targets.clusterIds
        
        if targets.selector:
            logger.info(f"Resolving clusters with selector: {targets.selector.matchLabels}")
            return await self._resolve_clusters_by_selector(targets.selector)
        
        raise ValueError("No valid target specification provided")
    
    async def _resolve_clusters_by_selector(self, selector: TargetSelector) -> List[str]:
        """Resolve clusters using label selector."""
        clusters = await self.get_clusters()
        matched_clusters = []
        
        for cluster in clusters:
            cluster_labels = cluster.get("labels", {})
            
            # Check if all selector labels match
            matches = all(
                cluster_labels.get(key) == value
                for key, value in selector.matchLabels.items()
            )
            
            if matches:
                cluster_id = cluster.get("id")
                if cluster_id:
                    matched_clusters.append(cluster_id)
                    logger.info(f"Matched cluster: {cluster_id} ({cluster.get('name', 'unknown')})")
        
        if not matched_clusters:
            logger.warning(f"No clusters matched selector: {selector.matchLabels}")
        
        return matched_clusters
    
    async def get_cluster_info(self, cluster_id: str) -> Dict[str, Any]:
        """Get information about a specific cluster."""
        try:
            return self._make_request("GET", f"clusters/{cluster_id}")
        except RancherAPIError:
            logger.error(f"Failed to get info for cluster: {cluster_id}")
            raise
    
    def list_apps(self, cluster_id: str, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List apps in a cluster."""
        endpoint = f"clusters/{cluster_id}/v1/apps"
        if namespace:
            endpoint += f"?namespace={namespace}"
        
        response = self._make_request("GET", endpoint)
        return response.get("data", [])
    
    def get_app(self, cluster_id: str, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific app by name."""
        apps = self.list_apps(cluster_id, namespace)
        for app in apps:
            if app.get("name") == name:
                return app
        return None
    
    async def ensure_namespace_exists(self, cluster_id: str, namespace: str) -> bool:
        """Ensure a namespace exists in the target cluster."""
        try:
            # For now, let's skip namespace creation and let Rancher handle it
            # The createNamespace: true in the app spec should handle this
            logger.info(f"Skipping namespace check - letting Rancher handle namespace creation for {namespace}")
            return True
        except Exception as e:
            logger.error(f"Error in namespace handling for {namespace} in cluster {cluster_id}: {e}")
            return False

    async def create_or_update_app(
        self,
        cluster_id: str,
        chart: Chart,
        values: Dict[str, Any]
    ) -> ChartDeployment:
        """Create or update a Helm app via Rancher Apps v2 API."""
        from datetime import datetime
        
        start_time = datetime.utcnow().isoformat() + "Z"
        
        try:
            # Ensure namespace exists if createNamespace is enabled
            if chart.createNamespace:
                namespace_created = await self.ensure_namespace_exists(cluster_id, chart.namespace)
                if not namespace_created:
                    raise Exception(f"Failed to ensure namespace {chart.namespace} exists")
            
            # Check if app already exists
            existing_app = self.get_app(cluster_id, chart.namespace, chart.releaseName)
            
            app_spec = {
                "name": chart.releaseName,
                "namespace": chart.namespace,
                "spec": {
                    "chart": {
                        "chartName": chart.name,
                        "version": chart.version,
                        "values": values
                    },
                    "createNamespace": chart.createNamespace,
                    "wait": chart.wait,
                    "timeout": chart.timeout
                }
            }
            
            if chart.repo:
                app_spec["spec"]["chart"]["repo"] = chart.repo
            
            if existing_app:
                logger.info(f"Updating existing app {chart.releaseName} in cluster {cluster_id}")
                response = self._make_request(
                    "PUT",
                    f"clusters/{cluster_id}/v1/apps/{chart.namespace}/{chart.releaseName}",
                    json=app_spec
                )
            else:
                logger.info(f"Creating new app {chart.releaseName} in cluster {cluster_id}")
                response = self._make_request(
                    "POST",
                    f"clusters/{cluster_id}/v1/apps",
                    json=app_spec
                )
            
            end_time = datetime.utcnow().isoformat() + "Z"
            
            return ChartDeployment(
                chartName=chart.name,
                clusterId=cluster_id,
                releaseName=chart.releaseName,
                namespace=chart.namespace,
                version=chart.version,
                status=ChartDeploymentStatus.DEPLOYED,
                message="Deployment successful",
                lastUpdated=end_time
            )
            
        except Exception as e:
            logger.error(f"Failed to deploy {chart.name} to cluster {cluster_id}: {e}")
            end_time = datetime.utcnow().isoformat() + "Z"
            
            return ChartDeployment(
                chartName=chart.name,
                clusterId=cluster_id,
                releaseName=chart.releaseName,
                namespace=chart.namespace,
                version=chart.version,
                status=ChartDeploymentStatus.FAILED,
                message=str(e),
                lastUpdated=end_time
            )
    
    async def delete_app(self, cluster_id: str, namespace: str, name: str) -> bool:
        """Delete an app from a cluster."""
        try:
            self._make_request(
                "DELETE",
                f"clusters/{cluster_id}/v1/apps/{namespace}/{name}"
            )
            logger.info(f"Deleted app {name} from cluster {cluster_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete app {name} from cluster {cluster_id}: {e}")
            return False
    
    async def wait_for_app_ready(self, cluster_id: str, namespace: str, name: str, timeout: int = 600) -> bool:
        """Wait for an app to become ready."""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                app = self.get_app(cluster_id, namespace, name)
                if app:
                    status = app.get("status", {})
                    if status.get("state") == "deployed":
                        return True
                    elif status.get("state") in ["failed", "error"]:
                        logger.error(f"App {name} failed to deploy: {status.get('message', 'Unknown error')}")
                        return False
                
                await asyncio.sleep(5)  # Wait 5 seconds before checking again
                
            except Exception as e:
                logger.warning(f"Error checking app status: {e}")
                await asyncio.sleep(5)
        
        logger.error(f"Timeout waiting for app {name} to become ready")
        return False
