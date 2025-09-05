"""
Kubernetes-native values merging logic for Helm charts.
"""

import yaml
import logging
from typing import Dict, Any, Optional
from copy import deepcopy
import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException

from .models import ChartValues, ConfigMapRef, SecretRef

logger = logging.getLogger(__name__)


class KubernetesValuesMerger:
    """Handles merging of Helm values from Kubernetes ConfigMaps and Secrets."""
    
    def __init__(self):
        """Initialize the values merger."""
        self.core_v1 = k8s_client.CoreV1Api()
    
    async def merge_values(
        self,
        chart_values: ChartValues,
        env: str,
        cluster_id: str,
        namespace: str
    ) -> Dict[str, Any]:
        """Merge values from all sources in the correct precedence order.
        
        Precedence (lowest to highest):
        1. ConfigMap references (base values)
        2. Environment overlay ConfigMap (auto-discovered)
        3. Per-cluster override ConfigMap
        4. Secret references
        5. Inline values
        
        Args:
            chart_values: ChartValues object from the chart specification
            env: Environment name (e.g., 'prod', 'staging')
            cluster_id: Target cluster ID
            namespace: Namespace to look for ConfigMaps/Secrets
            
        Returns:
            Merged values dictionary
        """
        merged = {}
        
        # 1. Load base values from ConfigMap references
        if chart_values.configMapRefs:
            for config_ref in chart_values.configMapRefs:
                values = await self._load_from_configmap(config_ref, namespace)
                if values:
                    merged = self._deep_merge(merged, values)
                    logger.debug(f"Merged values from ConfigMap {config_ref.name}")
        
        # 2. Load environment overlay
        env_values = await self._load_env_overlay(env, namespace)
        if env_values:
            merged = self._deep_merge(merged, env_values)
            logger.debug(f"Merged environment overlay for {env}")
        
        # 3. Load per-cluster overrides
        if chart_values.perClusterConfigMapRef:
            cluster_values = await self._load_cluster_override(
                chart_values.perClusterConfigMapRef, cluster_id, namespace
            )
            if cluster_values:
                merged = self._deep_merge(merged, cluster_values)
                logger.debug(f"Merged cluster override for {cluster_id}")
        
        # 4. Load values from Secret references
        if chart_values.secretRefs:
            for secret_ref in chart_values.secretRefs:
                values = await self._load_from_secret(secret_ref, namespace)
                if values:
                    merged = self._deep_merge(merged, values)
                    logger.debug(f"Merged values from Secret {secret_ref.name}")
        
        # 5. Apply inline values (highest precedence)
        if chart_values.inline:
            merged = self._deep_merge(merged, chart_values.inline)
            logger.debug("Merged inline values")
        
        return merged
    
    async def _load_from_configmap(self, config_ref: ConfigMapRef, default_namespace: str) -> Optional[Dict[str, Any]]:
        """Load values from a ConfigMap."""
        try:
            namespace = config_ref.namespace or default_namespace
            
            configmap = self.core_v1.read_namespaced_config_map(
                name=config_ref.name,
                namespace=namespace
            )
            
            if config_ref.key not in configmap.data:
                logger.warning(f"Key '{config_ref.key}' not found in ConfigMap {namespace}/{config_ref.name}")
                return None
            
            yaml_content = configmap.data[config_ref.key]
            values = yaml.safe_load(yaml_content)
            
            logger.info(f"Loaded values from ConfigMap {namespace}/{config_ref.name}")
            return values or {}
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"ConfigMap {namespace}/{config_ref.name} not found")
            else:
                logger.error(f"Failed to load ConfigMap {namespace}/{config_ref.name}: {e}")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML from ConfigMap {namespace}/{config_ref.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading ConfigMap {namespace}/{config_ref.name}: {e}")
            return None
    
    async def _load_from_secret(self, secret_ref: SecretRef, default_namespace: str) -> Optional[Dict[str, Any]]:
        """Load values from a Secret."""
        try:
            namespace = secret_ref.namespace or default_namespace
            
            secret = self.core_v1.read_namespaced_secret(
                name=secret_ref.name,
                namespace=namespace
            )
            
            if secret_ref.key not in secret.data:
                logger.warning(f"Key '{secret_ref.key}' not found in Secret {namespace}/{secret_ref.name}")
                return None
            
            # Decode base64 content
            import base64
            yaml_content = base64.b64decode(secret.data[secret_ref.key]).decode('utf-8')
            values = yaml.safe_load(yaml_content)
            
            logger.info(f"Loaded values from Secret {namespace}/{secret_ref.name}")
            return values or {}
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Secret {namespace}/{secret_ref.name} not found")
            else:
                logger.error(f"Failed to load Secret {namespace}/{secret_ref.name}: {e}")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML from Secret {namespace}/{secret_ref.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading Secret {namespace}/{secret_ref.name}: {e}")
            return None
    
    async def _load_env_overlay(self, env: str, namespace: str) -> Optional[Dict[str, Any]]:
        """Load environment-specific overlay values."""
        # Look for common environment overlay ConfigMaps
        env_configmap_names = [
            f"herd-env-{env}",
            f"stack-env-{env}",
            f"values-{env}",
            f"{env}-values"
        ]
        
        for configmap_name in env_configmap_names:
            config_ref = ConfigMapRef(name=configmap_name, key="values.yaml")
            values = await self._load_from_configmap(config_ref, namespace)
            if values:
                return values
        
        logger.debug(f"No environment overlay found for {env}")
        return None
    
    async def _load_cluster_override(
        self,
        config_ref: ConfigMapRef,
        cluster_id: str,
        default_namespace: str
    ) -> Optional[Dict[str, Any]]:
        """Load per-cluster override values."""
        try:
            namespace = config_ref.namespace or default_namespace
            
            configmap = self.core_v1.read_namespaced_config_map(
                name=config_ref.name,
                namespace=namespace
            )
            
            # Look for cluster-specific key
            cluster_key = f"{cluster_id}.yaml"
            if cluster_key not in configmap.data:
                logger.debug(f"No cluster override found for {cluster_id}")
                return None
            
            yaml_content = configmap.data[cluster_key]
            values = yaml.safe_load(yaml_content)
            
            logger.info(f"Loaded cluster override for {cluster_id}")
            return values or {}
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Per-cluster ConfigMap {namespace}/{config_ref.name} not found")
            else:
                logger.error(f"Failed to load per-cluster ConfigMap: {e}")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse cluster override YAML: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading cluster override: {e}")
            return None
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        The overlay values take precedence over base values.
        For nested dictionaries, recursively merge.
        For lists, the overlay replaces the base (no merging).
        """
        if not isinstance(base, dict) or not isinstance(overlay, dict):
            return overlay
        
        result = deepcopy(base)
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Replace value (including lists)
                result[key] = deepcopy(value)
        
        return result
    
    def validate_values(self, values: Dict[str, Any]) -> List[str]:
        """Validate merged values and return any warnings."""
        warnings = []
        
        # Check for common issues
        if not values:
            warnings.append("Values dictionary is empty")
        
        # Check for potentially problematic structures
        def check_nested(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    current_path = f"{path}.{k}" if path else k
                    if k.startswith('_'):
                        warnings.append(f"Key '{current_path}' starts with underscore (may cause issues)")
                    check_nested(v, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_nested(item, f"{path}[{i}]")
        
        check_nested(values)
        
        return warnings
