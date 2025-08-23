"""
Plugin Loader and Manifest Validation System

Manages loading, validating, and managing legal domain plugins.
Enables domain experts to extend the system without modifying core code.
"""

from __future__ import annotations
import importlib.util
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError

from sdk.plugin import (
    OntologyProvider, MappingProvider, RuleProvider, 
    LegalExplainer, ValidationProvider
)


class PluginManifest(BaseModel):
    """
    Validated plugin manifest with required metadata
    
    Defines plugin capabilities, jurisdiction support, and dependencies
    following the legal-hypergraph-plugin schema.
    """
    schema: str = Field(..., description="Plugin schema version")
    id: str = Field(..., description="Unique plugin identifier")
    version: str = Field(..., description="Plugin version (semver)")
    displayName: str = Field(..., description="Human-readable plugin name")
    domains: List[str] = Field(..., description="Legal domains covered")
    jurisdictions: List[Dict[str, Any]] = Field(..., description="Supported jurisdictions")
    capabilities: Dict[str, Any] = Field(..., description="Plugin capabilities")
    
    # Optional fields for advanced plugins
    models: Optional[Dict[str, str]] = Field(None, description="ML model specifications")
    ontology: Optional[Dict[str, Any]] = Field(None, description="Ontology metadata")
    reasoning: Optional[Dict[str, Any]] = Field(None, description="Reasoning capabilities")


class Plugin:
    """
    Loaded plugin with all providers and capability detection
    
    Wraps the plugin manifest and loaded Python module, providing
    access to domain-specific providers and capability validation.
    """
    
    def __init__(self, manifest: PluginManifest, module):
        """
        Initialize plugin with manifest and loaded module
        
        Args:
            manifest: Validated plugin manifest
            module: Loaded Python module containing providers
        """
        self.manifest = manifest
        self.module = module
        
        # Load providers from module attributes
        self.ontology: Optional[OntologyProvider] = getattr(module, "ontology", None)
        self.mapping: Optional[MappingProvider] = getattr(module, "mapping", None)
        self.rules: Optional[RuleProvider] = getattr(module, "rules", None)
        self.explainer: Optional[LegalExplainer] = getattr(module, "explainer", None)
        self.validator: Optional[ValidationProvider] = getattr(module, "validator", None)
        
    @property
    def provides_ontology(self) -> bool:
        """Check if plugin provides ontology capability"""
        return self.ontology is not None
        
    @property
    def provides_mapping(self) -> bool:
        """Check if plugin provides mapping/extraction capability"""
        return self.mapping is not None
        
    @property
    def provides_rules(self) -> bool:
        """Check if plugin provides rule capability"""
        return self.rules is not None
        
    @property
    def provides_explanation(self) -> bool:
        """Check if plugin provides explanation capability"""
        return self.explainer is not None
        
    @property
    def provides_validation(self) -> bool:
        """Check if plugin provides validation capability"""
        return self.validator is not None


class PluginLoader:
    """
    Manages plugin loading, validation, and lifecycle
    
    Discovers plugins from directories, validates manifests and capabilities,
    loads Python modules, and manages the registry of loaded plugins.
    """
    
    def __init__(self, plugin_dir: str = "plugins"):
        """
        Initialize plugin loader
        
        Args:
            plugin_dir: Base directory for plugin discovery
        """
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: Dict[str, Plugin] = {}
        
    def load_plugin(self, plugin_path: str) -> Plugin:
        """
        Load and validate a plugin from directory
        
        Args:
            plugin_path: Path to plugin directory
            
        Returns:
            Loaded and validated plugin
            
        Raises:
            FileNotFoundError: If manifest or module files are missing
            ValueError: If manifest is invalid or capabilities don't match
        """
        plugin_dir = Path(plugin_path)
        
        # Load and validate manifest
        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Plugin manifest not found: {manifest_path}")
            
        with open(manifest_path, 'r') as f:
            manifest_data = yaml.safe_load(f)
            
        try:
            manifest = PluginManifest.model_validate(manifest_data)
        except ValidationError as e:
            raise ValueError(f"Invalid plugin manifest: {e}")
            
        # Load Python module
        module_path = plugin_dir / "module.py"
        if not module_path.exists():
            raise FileNotFoundError(f"Plugin module not found: {module_path}")
            
        # Load module dynamically
        spec = importlib.util.spec_from_file_location(manifest.id, module_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load module spec for {manifest.id}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Create plugin instance
        plugin = Plugin(manifest, module)
        
        # Validate plugin provides claimed capabilities
        self._validate_capabilities(plugin)
        
        # Cache plugin
        self.loaded_plugins[manifest.id] = plugin
        
        return plugin
        
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get loaded plugin by ID
        
        Args:
            plugin_id: Unique plugin identifier
            
        Returns:
            Loaded plugin or None if not found
        """
        return self.loaded_plugins.get(plugin_id)
        
    def list_plugins(self) -> List[str]:
        """
        List all loaded plugin IDs
        
        Returns:
            List of plugin identifiers
        """
        return list(self.loaded_plugins.keys())
        
    def _validate_capabilities(self, plugin: Plugin) -> None:
        """
        Validate plugin provides claimed capabilities
        
        Args:
            plugin: Plugin to validate
            
        Raises:
            ValueError: If plugin claims capabilities it doesn't provide
        """
        capabilities = plugin.manifest.capabilities
        provides = capabilities.get("provides", [])
        
        # Check each claimed capability has corresponding provider
        if "ontology" in provides and not plugin.provides_ontology:
            raise ValueError(f"Plugin {plugin.manifest.id} claims to provide ontology but doesn't")
            
        if "mapping" in provides and not plugin.provides_mapping:
            raise ValueError(f"Plugin {plugin.manifest.id} claims to provide mapping but doesn't")
            
        if "rules" in provides and not plugin.provides_rules:
            raise ValueError(f"Plugin {plugin.manifest.id} claims to provide rules but doesn't")
            
        if "explainer" in provides and not plugin.provides_explanation:
            raise ValueError(f"Plugin {plugin.manifest.id} claims to provide explainer but doesn't")
            
        if "validator" in provides and not plugin.provides_validation:
            raise ValueError(f"Plugin {plugin.manifest.id} claims to provide validator but doesn't")
            
    def discover_plugins(self, directory: Optional[str] = None) -> List[str]:
        """
        Discover available plugins in directory
        
        Args:
            directory: Directory to search (defaults to plugin_dir)
            
        Returns:
            List of discovered plugin directory paths
        """
        search_dir = Path(directory) if directory else self.plugin_dir
        
        if not search_dir.exists():
            return []
            
        plugin_paths = []
        for item in search_dir.iterdir():
            if item.is_dir() and (item / "plugin.yaml").exists():
                plugin_paths.append(str(item))
                
        return plugin_paths
        
    def load_all_plugins(self, directory: Optional[str] = None) -> Dict[str, Plugin]:
        """
        Discover and load all plugins in directory
        
        Args:
            directory: Directory to search (defaults to plugin_dir)
            
        Returns:
            Dictionary of plugin_id -> Plugin for successfully loaded plugins
        """
        plugin_paths = self.discover_plugins(directory)
        loaded = {}
        
        for plugin_path in plugin_paths:
            try:
                plugin = self.load_plugin(plugin_path)
                loaded[plugin.manifest.id] = plugin
            except Exception as e:
                # Log error but continue loading other plugins
                print(f"Failed to load plugin at {plugin_path}: {e}")
                continue
                
        return loaded