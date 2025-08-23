"""
TDD Tests for Plugin Loader and Manifest Validation

Following Test-Driven Development methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up and optimize

Tests cover plugin manifest validation, loading, and capability validation.
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge
from sdk.plugin import (
    RawDoc, OntologyProvider, MappingProvider, RuleProvider, 
    LegalExplainer, ValidationProvider
)
from core.loader import PluginManifest, Plugin, PluginLoader


class TestPluginManifest:
    """Test the plugin manifest validation"""
    
    def test_plugin_manifest_creation(self):
        """
        TDD: PluginManifest should validate required plugin metadata
        """
        manifest_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "employment-law",
            "version": "1.0.0",
            "displayName": "Employment Law Plugin",
            "domains": ["employment", "ada", "flsa"],
            "jurisdictions": [{"code": "US", "name": "United States"}],
            "capabilities": {
                "provides": ["ontology", "mapping", "rules", "explainer"]
            }
        }
        
        manifest = PluginManifest.model_validate(manifest_data)
        
        assert manifest.id == "employment-law"
        assert manifest.version == "1.0.0"
        assert "employment" in manifest.domains
        assert manifest.capabilities["provides"] == ["ontology", "mapping", "rules", "explainer"]
        
    def test_plugin_manifest_validation_missing_required(self):
        """
        TDD: PluginManifest should require essential fields
        """
        incomplete_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "test-plugin"
            # Missing required fields
        }
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            PluginManifest.model_validate(incomplete_data)
            
    def test_plugin_manifest_optional_fields(self):
        """
        TDD: PluginManifest should support optional fields
        """
        manifest_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "test-plugin",
            "version": "1.0.0",
            "displayName": "Test Plugin",
            "domains": ["test"],
            "jurisdictions": [{"code": "US", "name": "United States"}],
            "capabilities": {"provides": ["ontology"]},
            "models": {"ner": "legal-bert-ner", "embeddings": "legal-bert-base"},
            "ontology": {"classes": 50, "properties": 25},
            "reasoning": {"rules": 100, "exceptions": 20}
        }
        
        manifest = PluginManifest.model_validate(manifest_data)
        
        assert manifest.models["ner"] == "legal-bert-ner"
        assert manifest.ontology["classes"] == 50
        assert manifest.reasoning["rules"] == 100


class TestPlugin:
    """Test the plugin wrapper class"""
    
    def test_plugin_creation_with_providers(self):
        """
        TDD: Plugin should wrap manifest and module with provider detection
        """
        # Create a test module with providers
        class TestModule:
            def __init__(self):
                self.ontology = TestOntologyProvider()
                self.mapping = TestMappingProvider()
                self.rules = None  # Missing provider
                self.explainer = None
                self.validator = None
        
        # Test provider implementations
        class TestOntologyProvider(OntologyProvider):
            def classes(self) -> List[Dict[str, Any]]:
                return [{"name": "Employee", "description": "Person employed"}]
            def properties(self) -> List[Dict[str, Any]]:
                return [{"name": "employs", "domain": "Employer", "range": "Employee"}]
            def constraints(self) -> List[Dict[str, Any]]:
                return []
                
        class TestMappingProvider(MappingProvider):
            def extract_entities(self, doc: RawDoc, ctx: Optional[Context] = None) -> List[Node]:
                return []
            def extract_relations(self, nodes: List[Node], doc: RawDoc, 
                                ctx: Optional[Context] = None) -> List[Hyperedge]:
                return []
            def extract_obligations(self, doc: RawDoc, 
                                  ctx: Optional[Context] = None) -> List[Hyperedge]:
                return []
        
        manifest_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "test-plugin",
            "version": "1.0.0",
            "displayName": "Test Plugin",
            "domains": ["test"],
            "jurisdictions": [{"code": "US", "name": "United States"}],
            "capabilities": {"provides": ["ontology", "mapping"]}
        }
        
        manifest = PluginManifest.model_validate(manifest_data)
        module = TestModule()
        plugin = Plugin(manifest, module)
        
        assert plugin.manifest.id == "test-plugin"
        assert plugin.provides_ontology is True
        assert plugin.provides_mapping is True
        assert plugin.provides_rules is False
        assert plugin.provides_explanation is False
        
    def test_plugin_provider_access(self):
        """
        TDD: Plugin should provide access to loaded providers
        """
        class TestModule:
            def __init__(self):
                self.ontology = "fake_ontology_provider"
                
        manifest_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "test-plugin",
            "version": "1.0.0",
            "displayName": "Test Plugin",
            "domains": ["test"],
            "jurisdictions": [{"code": "US", "name": "United States"}],
            "capabilities": {"provides": ["ontology"]}
        }
        
        manifest = PluginManifest.model_validate(manifest_data)
        module = TestModule()
        plugin = Plugin(manifest, module)
        
        assert plugin.ontology == "fake_ontology_provider"
        assert plugin.mapping is None


class TestPluginLoader:
    """Test the plugin loader system"""
    
    def test_plugin_loader_initialization(self):
        """
        TDD: PluginLoader should initialize with plugin directory
        """
        loader = PluginLoader("test_plugins")
        assert str(loader.plugin_dir) == "test_plugins"
        assert len(loader.loaded_plugins) == 0
        
    def test_load_plugin_from_directory(self):
        """
        TDD: PluginLoader should load valid plugins from directories
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Create plugin manifest
            manifest_data = {
                "schema": "legal-hypergraph-plugin/v1",
                "id": "test-plugin",
                "version": "1.0.0",
                "displayName": "Test Plugin",
                "domains": ["test"],
                "jurisdictions": [{"code": "US", "name": "United States"}],
                "capabilities": {"provides": ["ontology"]}
            }
            
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(manifest_data, f)
                
            # Create plugin module
            module_code = '''
from sdk.plugin import OntologyProvider
from typing import List, Dict, Any

class TestOntology(OntologyProvider):
    def classes(self) -> List[Dict[str, Any]]:
        return [{"name": "TestClass", "description": "A test class"}]
    def properties(self) -> List[Dict[str, Any]]:
        return []
    def constraints(self) -> List[Dict[str, Any]]:
        return []

ontology = TestOntology()
'''
            
            with open(plugin_dir / "module.py", "w") as f:
                f.write(module_code)
                
            # Load the plugin
            loader = PluginLoader()
            plugin = loader.load_plugin(str(plugin_dir))
            
            assert plugin.manifest.id == "test-plugin"
            assert plugin.provides_ontology is True
            assert "test-plugin" in loader.loaded_plugins
            
    def test_load_plugin_missing_manifest(self):
        """
        TDD: PluginLoader should raise error for missing manifest
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "invalid_plugin"
            plugin_dir.mkdir()
            
            loader = PluginLoader()
            
            with pytest.raises(FileNotFoundError, match="Plugin manifest not found"):
                loader.load_plugin(str(plugin_dir))
                
    def test_load_plugin_missing_module(self):
        """
        TDD: PluginLoader should raise error for missing module
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "invalid_plugin"
            plugin_dir.mkdir()
            
            # Create manifest but no module
            manifest_data = {
                "schema": "legal-hypergraph-plugin/v1",
                "id": "invalid-plugin",
                "version": "1.0.0",
                "displayName": "Invalid Plugin",
                "domains": ["test"],
                "jurisdictions": [{"code": "US", "name": "United States"}],
                "capabilities": {"provides": []}
            }
            
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(manifest_data, f)
                
            loader = PluginLoader()
            
            with pytest.raises(FileNotFoundError, match="Plugin module not found"):
                loader.load_plugin(str(plugin_dir))
                
    def test_load_plugin_invalid_manifest(self):
        """
        TDD: PluginLoader should raise error for invalid manifest
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "invalid_plugin"
            plugin_dir.mkdir()
            
            # Create invalid manifest
            invalid_manifest = {"invalid": "data"}
            
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(invalid_manifest, f)
                
            loader = PluginLoader()
            
            with pytest.raises(ValueError, match="Invalid plugin manifest"):
                loader.load_plugin(str(plugin_dir))
                
    def test_plugin_capability_validation(self):
        """
        TDD: PluginLoader should validate claimed capabilities
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Create manifest claiming ontology capability
            manifest_data = {
                "schema": "legal-hypergraph-plugin/v1",
                "id": "test-plugin",
                "version": "1.0.0",
                "displayName": "Test Plugin",
                "domains": ["test"],
                "jurisdictions": [{"code": "US", "name": "United States"}],
                "capabilities": {"provides": ["ontology"]}  # Claims to provide ontology
            }
            
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(manifest_data, f)
                
            # Create module WITHOUT ontology provider
            module_code = '''
# No ontology provider defined
mapping = None
'''
            
            with open(plugin_dir / "module.py", "w") as f:
                f.write(module_code)
                
            loader = PluginLoader()
            
            with pytest.raises(ValueError, match="claims to provide ontology but doesn't"):
                loader.load_plugin(str(plugin_dir))
                
    def test_get_plugin_by_id(self):
        """
        TDD: PluginLoader should retrieve loaded plugins by ID
        """
        loader = PluginLoader()
        
        # No plugin loaded yet
        assert loader.get_plugin("nonexistent") is None
        
        # Mock a loaded plugin
        manifest_data = {
            "schema": "legal-hypergraph-plugin/v1",
            "id": "mock-plugin",
            "version": "1.0.0",
            "displayName": "Mock Plugin",
            "domains": ["test"],
            "jurisdictions": [{"code": "US", "name": "United States"}],
            "capabilities": {"provides": []}
        }
        
        manifest = PluginManifest.model_validate(manifest_data)
        plugin = Plugin(manifest, type('MockModule', (), {})())
        loader.loaded_plugins["mock-plugin"] = plugin
        
        # Should retrieve the plugin
        retrieved = loader.get_plugin("mock-plugin")
        assert retrieved is not None
        assert retrieved.manifest.id == "mock-plugin"
        
    def test_list_loaded_plugins(self):
        """
        TDD: PluginLoader should list all loaded plugin IDs
        """
        loader = PluginLoader()
        
        # No plugins loaded
        assert loader.list_plugins() == []
        
        # Mock some loaded plugins
        for plugin_id in ["plugin1", "plugin2", "plugin3"]:
            manifest_data = {
                "schema": "legal-hypergraph-plugin/v1",
                "id": plugin_id,
                "version": "1.0.0",
                "displayName": f"Plugin {plugin_id}",
                "domains": ["test"],
                "jurisdictions": [{"code": "US", "name": "United States"}],
                "capabilities": {"provides": []}
            }
            
            manifest = PluginManifest.model_validate(manifest_data)
            plugin = Plugin(manifest, type('MockModule', (), {})())
            loader.loaded_plugins[plugin_id] = plugin
            
        plugin_list = loader.list_plugins()
        assert len(plugin_list) == 3
        assert "plugin1" in plugin_list
        assert "plugin2" in plugin_list
        assert "plugin3" in plugin_list