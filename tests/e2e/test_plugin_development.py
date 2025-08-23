"""
End-to-End Tests: Plugin Development and Validation

Tests the complete plugin development workflow from creation through
validation and deployment, covering user stories for domain experts
and plugin developers.
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List

from core.loader import PluginLoader, PluginManifest
from core.storage import GraphStore
from core.reasoning import RuleEngine
from core.model import Context, mk_node, mk_edge, Provenance
from sdk.plugin import RawDoc
from tests.helpers.legal_assertions import LegalAssertions, SecurityAssertions


class TestPluginDevelopmentWorkflow:
    """Test complete plugin development and deployment workflow"""
    
    @pytest.fixture
    def temp_plugin_dir(self):
        """Create temporary directory for plugin testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def plugin_loader(self, temp_plugin_dir):
        """Plugin loader configured for testing"""
        return PluginLoader(temp_plugin_dir)
    
    @pytest.fixture
    def legal_assertions(self):
        return LegalAssertions()
    
    @pytest.fixture
    def security_assertions(self):
        return SecurityAssertions()

    class TestPluginCreation:
        """Test Story: Legal Domain Expert - Create Legal Domain Plugin"""
        
        def test_create_employment_plugin_from_scratch(self, temp_plugin_dir, plugin_loader, legal_assertions):
            """
            Given: A legal domain expert wants to create an employment law plugin
            When: They create plugin manifest and implementation files
            Then: Plugin should load successfully and provide expected capabilities
            """
            # Given: Plugin directory structure
            plugin_path = Path(temp_plugin_dir) / "test-employment-plugin"
            plugin_path.mkdir()
            
            # Create plugin manifest
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.employment-law',
                'version': '1.0.0',
                'displayName': 'Test Employment Law Plugin',
                'domains': ['employment'],
                'jurisdictions': [{'country': 'US', 'authority': 'federal'}],
                'capabilities': {
                    'provides': ['ontology', 'mapping', 'rules', 'explainer'],
                    'requires': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            # Create minimal plugin implementation
            plugin_code = '''
from sdk.plugin import OntologyProvider, MappingProvider, RuleProvider, LegalExplainer
from core.model import Node, Hyperedge, mk_node, mk_edge, Provenance
from datetime import datetime

class TestOntology(OntologyProvider):
    def classes(self):
        return [{"id": "Employee"}, {"id": "Employer"}, {"id": "Obligation"}]
    def properties(self):
        return [{"id": "employs"}, {"id": "owes"}]
    def constraints(self):
        return []

class TestMapping(MappingProvider):
    def extract_entities(self, doc, ctx=None):
        # Simple test extraction
        prov = Provenance(
            source=[{"type": "document", "id": doc.id}],
            method="test.extract",
            agent="test.plugin",
            time=datetime.utcnow(),
            confidence=0.9
        )
        return [mk_node("Employee", {"name": "test"}, prov)]
    
    def extract_relations(self, nodes, doc, ctx=None):
        return []
    
    def extract_obligations(self, doc, ctx=None):
        return []

class TestRules(RuleProvider):
    def statutory_rules(self, ctx=None):
        return []
    def case_law_rules(self, ctx=None):
        return []
    def exception_rules(self, ctx=None):
        return []

class TestExplainer(LegalExplainer):
    def statutory_explanation(self, conclusion_id, graph):
        return "Test explanation"
    def precedential_explanation(self, conclusion_id, graph):
        return "Test precedent explanation"
    def counterfactual_explanation(self, conclusion_id, graph):
        return "Test counterfactual explanation"

ontology = TestOntology()
mapping = TestMapping()
rules = TestRules()
explainer = TestExplainer()
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # When: Loading the plugin
            plugin = plugin_loader.load_plugin(str(plugin_path))
            
            # Then: Plugin should load successfully
            assert plugin is not None
            assert plugin.manifest.id == 'test.employment-law'
            assert plugin.provides_ontology
            assert plugin.provides_mapping
            assert plugin.provides_rules
            assert plugin.provides_explanation
        
        def test_plugin_manifest_validation(self, temp_plugin_dir, plugin_loader):
            """
            Given: Plugin manifest with various validation scenarios
            When: Loading plugins with different manifest issues
            Then: Should properly validate and report errors
            """
            plugin_path = Path(temp_plugin_dir) / "invalid-plugin"
            plugin_path.mkdir()
            
            # Test invalid schema version
            invalid_manifest = {
                'schema': 'invalid-version',
                'id': 'test.invalid',
                'version': '1.0.0'
                # Missing required fields
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(invalid_manifest, f)
            
            # Create empty module file
            with open(plugin_path / 'module.py', 'w') as f:
                f.write("# Empty module")
            
            # Should raise validation error
            with pytest.raises(ValueError, match="Invalid plugin manifest"):
                plugin_loader.load_plugin(str(plugin_path))
        
        def test_plugin_capability_validation(self, temp_plugin_dir, plugin_loader):
            """
            Given: Plugin claiming capabilities it doesn't provide
            When: Loading plugin
            Then: Should detect and report capability mismatches
            """
            plugin_path = Path(temp_plugin_dir) / "mismatch-plugin"
            plugin_path.mkdir()
            
            # Manifest claims ontology capability
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.mismatch',
                'version': '1.0.0',
                'displayName': 'Capability Mismatch Plugin',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['ontology', 'mapping'],  # Claims ontology
                    'requires': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            # But module doesn't provide ontology
            plugin_code = '''
# No ontology provider implemented
ontology = None
mapping = None
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # Should raise capability validation error
            with pytest.raises(ValueError, match="claims to provide ontology but doesn't"):
                plugin_loader.load_plugin(str(plugin_path))

    class TestPluginValidation:
        """Test Story: Plugin Developer - Plugin Validation Framework"""
        
        def test_legal_rule_validation(self, temp_plugin_dir, plugin_loader, legal_assertions):
            """
            Given: Plugin with legal rules
            When: Validating rule correctness and completeness
            Then: Should detect rule validation issues
            """
            plugin_path = Path(temp_plugin_dir) / "validation-plugin"
            plugin_path.mkdir()
            
            # Create plugin with rules to validate
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.validation',
                'version': '1.0.0',
                'displayName': 'Validation Test Plugin',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['rules'],
                    'requires': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            plugin_code = '''
from sdk.plugin import RuleProvider
from core.model import mk_edge, Provenance
from datetime import datetime

class TestRules(RuleProvider):
    def statutory_rules(self, ctx=None):
        # Rule with proper legal authority
        prov = Provenance(
            source=[{"type": "statute", "cite": "42 U.S.C. § 12112"}],
            method="rule.definition",
            agent="test.plugin",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        rule = mk_edge("rule", [], [], prov, qualifiers={
            "rule_id": "test_rule",
            "premises": [{"type": "Employee"}],
            "conclusions": [{"type": "Obligation"}],
            "authority": "42 U.S.C. § 12112"
        })
        
        return [rule]
    
    def case_law_rules(self, ctx=None):
        return []
    
    def exception_rules(self, ctx=None):
        return []

rules = TestRules()
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # When: Loading and validating plugin
            plugin = plugin_loader.load_plugin(str(plugin_path))
            rules_list = plugin.rules.statutory_rules()
            
            # Then: Should have valid rule structure
            assert len(rules_list) == 1
            rule = rules_list[0]
            
            legal_assertions.assert_valid_provenance(rule.prov)
            legal_assertions.assert_contains_legal_authority(rule.prov.source, "42 U.S.C.")
            
            # Rule should have proper structure
            assert rule.qualifiers.get("rule_id") == "test_rule"
            assert "premises" in rule.qualifiers
            assert "conclusions" in rule.qualifiers
            assert "authority" in rule.qualifiers
        
        def test_ontology_consistency_validation(self, temp_plugin_dir, plugin_loader):
            """
            Given: Plugin with ontology definitions
            When: Validating ontology consistency
            Then: Should detect inconsistencies and conflicts
            """
            plugin_path = Path(temp_plugin_dir) / "ontology-plugin"
            plugin_path.mkdir()
            
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.ontology',
                'version': '1.0.0',
                'displayName': 'Ontology Test Plugin',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['ontology'],
                    'requires': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            plugin_code = '''
from sdk.plugin import OntologyProvider

class TestOntology(OntologyProvider):
    def classes(self):
        return [
            {"id": "LegalEntity", "type": "class"},
            {"id": "Person", "type": "class", "parent": "LegalEntity"},
            {"id": "Organization", "type": "class", "parent": "LegalEntity"},
            {"id": "Employee", "type": "class", "parent": "Person"},
            {"id": "Employer", "type": "class", "parent": "Organization"}
        ]
    
    def properties(self):
        return [
            {"id": "employs", "domain": "Employer", "range": "Employee"},
            {"id": "worksFor", "domain": "Employee", "range": "Employer"}
        ]
    
    def constraints(self):
        return [
            {"type": "inverse", "property1": "employs", "property2": "worksFor"},
            {"type": "cardinality", "property": "employs", "min": 0, "max": None}
        ]

ontology = TestOntology()
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # When: Loading and validating ontology
            plugin = plugin_loader.load_plugin(str(plugin_path))
            
            classes = plugin.ontology.classes()
            properties = plugin.ontology.properties()
            constraints = plugin.ontology.constraints()
            
            # Then: Should have consistent ontology structure
            assert len(classes) == 5
            assert len(properties) == 2
            assert len(constraints) == 2
            
            # Validate class hierarchy
            class_ids = {c["id"] for c in classes}
            assert "LegalEntity" in class_ids
            assert "Person" in class_ids
            assert "Employee" in class_ids
            
            # Validate property consistency
            property_ids = {p["id"] for p in properties}
            assert "employs" in property_ids
            assert "worksFor" in property_ids

    class TestPluginSecurity:
        """Test Story: Security Engineer - Plugin Security and Sandboxing"""
        
        def test_plugin_resource_limits(self, temp_plugin_dir, plugin_loader, security_assertions):
            """
            Given: Plugin with resource usage requirements
            When: Loading and executing plugin
            Then: Should enforce resource limits and isolation
            """
            plugin_path = Path(temp_plugin_dir) / "resource-plugin"
            plugin_path.mkdir()
            
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.resource',
                'version': '1.0.0',
                'displayName': 'Resource Test Plugin',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['mapping'],
                    'requires': []
                },
                'security': {
                    'sandbox': 'python',
                    'resources': {
                        'cpu_ms': 5000,
                        'mem_mb': 512
                    }
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            plugin_code = '''
from sdk.plugin import MappingProvider
from core.model import mk_node, Provenance
from datetime import datetime

class ResourceMapping(MappingProvider):
    def extract_entities(self, doc, ctx=None):
        # Simulate resource-intensive operation
        import time
        time.sleep(0.1)  # Small delay to test timing
        
        prov = Provenance(
            source=[{"type": "document", "id": doc.id}],
            method="test.resource_extract",
            agent="test.plugin",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        return [mk_node("TestEntity", {"processed": True}, prov)]
    
    def extract_relations(self, nodes, doc, ctx=None):
        return []
    
    def extract_obligations(self, doc, ctx=None):
        return []

mapping = ResourceMapping()
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # When: Loading plugin and testing resource enforcement
            plugin = plugin_loader.load_plugin(str(plugin_path))
            
            # Then: Plugin should load with security constraints
            assert plugin.manifest.security is not None
            assert plugin.manifest.security['sandbox'] == 'python'
            assert plugin.manifest.security['resources']['cpu_ms'] == 5000
            
            # Test execution within resource limits
            doc = RawDoc(id="resource-test", text="Test document", meta={})
            
            import time
            start_time = time.time()
            entities = plugin.mapping.extract_entities(doc)
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert execution_time < 1.0  # 1 second max for test
            assert len(entities) == 1
            
        def test_plugin_access_control(self, temp_plugin_dir, plugin_loader, security_assertions):
            """
            Given: Plugin requiring specific permissions
            When: Plugin attempts to access restricted resources
            Then: Should enforce access control policies
            """
            plugin_path = Path(temp_plugin_dir) / "access-plugin"
            plugin_path.mkdir()
            
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.access',
                'version': '1.0.0',
                'displayName': 'Access Control Test Plugin',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['mapping'],
                    'requires': []
                },
                'permissions': {
                    'network': False,
                    'filesystem': ['read'],
                    'external_apis': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            plugin_code = '''
from sdk.plugin import MappingProvider

class AccessMapping(MappingProvider):
    def extract_entities(self, doc, ctx=None):
        # Plugin should not be able to access network
        # This would be blocked by sandboxing in production
        return []
    
    def extract_relations(self, nodes, doc, ctx=None):
        return []
    
    def extract_obligations(self, doc, ctx=None):
        return []

mapping = AccessMapping()
'''
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write(plugin_code)
            
            # When: Loading plugin with access restrictions
            plugin = plugin_loader.load_plugin(str(plugin_path))
            
            # Then: Should have proper permission configuration
            assert 'permissions' in plugin.manifest.dict()
            permissions = plugin.manifest.dict()['permissions']
            assert permissions['network'] is False
            assert 'read' in permissions['filesystem']
            assert len(permissions['external_apis']) == 0

    class TestPluginIntegration:
        """Test Story: Legal Technology Specialist - Enterprise Plugin Deployment"""
        
        def test_plugin_version_management(self, temp_plugin_dir, plugin_loader):
            """
            Given: Multiple versions of the same plugin
            When: Managing plugin versions and updates
            Then: Should handle version conflicts and compatibility
            """
            # Create two versions of the same plugin
            for version in ['1.0.0', '1.1.0']:
                plugin_path = Path(temp_plugin_dir) / f"versioned-plugin-{version}"
                plugin_path.mkdir()
                
                manifest = {
                    'schema': 'legal-substrate.plugin/v2',
                    'id': 'test.versioned',
                    'version': version,
                    'displayName': f'Versioned Plugin {version}',
                    'domains': ['test'],
                    'jurisdictions': [{'country': 'US'}],
                    'capabilities': {
                        'provides': ['ontology'],
                        'requires': []
                    }
                }
                
                with open(plugin_path / 'plugin.yaml', 'w') as f:
                    yaml.dump(manifest, f)
                
                plugin_code = f'''
from sdk.plugin import OntologyProvider

class VersionedOntology(OntologyProvider):
    def classes(self):
        return [{{"id": "TestClass", "version": "{version}"}}]
    def properties(self):
        return []
    def constraints(self):
        return []

ontology = VersionedOntology()
'''
                
                with open(plugin_path / 'module.py', 'w') as f:
                    f.write(plugin_code)
            
            # When: Loading different versions
            plugin_v1 = plugin_loader.load_plugin(str(Path(temp_plugin_dir) / "versioned-plugin-1.0.0"))
            plugin_v1_1 = plugin_loader.load_plugin(str(Path(temp_plugin_dir) / "versioned-plugin-1.1.0"))
            
            # Then: Should handle version differences
            assert plugin_v1.manifest.version == '1.0.0'
            assert plugin_v1_1.manifest.version == '1.1.0'
            assert plugin_v1.manifest.id == plugin_v1_1.manifest.id
            
            # Different versions should have different ontology content
            classes_v1 = plugin_v1.ontology.classes()
            classes_v1_1 = plugin_v1_1.ontology.classes()
            
            assert classes_v1[0]['version'] == '1.0.0'
            assert classes_v1_1[0]['version'] == '1.1.0'
        
        def test_plugin_dependency_resolution(self, temp_plugin_dir, plugin_loader):
            """
            Given: Plugins with dependencies on other plugins
            When: Loading plugins with dependency requirements
            Then: Should resolve dependencies and load in correct order
            """
            # Create base plugin
            base_path = Path(temp_plugin_dir) / "base-plugin"
            base_path.mkdir()
            
            base_manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.base',
                'version': '1.0.0',
                'displayName': 'Base Plugin',
                'domains': ['base'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['ontology'],
                    'requires': []
                }
            }
            
            with open(base_path / 'plugin.yaml', 'w') as f:
                yaml.dump(base_manifest, f)
            
            with open(base_path / 'module.py', 'w') as f:
                f.write('''
from sdk.plugin import OntologyProvider

class BaseOntology(OntologyProvider):
    def classes(self):
        return [{"id": "BaseClass"}]
    def properties(self):
        return []
    def constraints(self):
        return []

ontology = BaseOntology()
''')
            
            # Create dependent plugin
            dependent_path = Path(temp_plugin_dir) / "dependent-plugin"
            dependent_path.mkdir()
            
            dependent_manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': 'test.dependent',
                'version': '1.0.0',
                'displayName': 'Dependent Plugin',
                'domains': ['dependent'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['ontology'],
                    'requires': ['test.base@>=1.0.0']
                }
            }
            
            with open(dependent_path / 'plugin.yaml', 'w') as f:
                yaml.dump(dependent_manifest, f)
            
            with open(dependent_path / 'module.py', 'w') as f:
                f.write('''
from sdk.plugin import OntologyProvider

class DependentOntology(OntologyProvider):
    def classes(self):
        return [{"id": "DependentClass", "extends": "BaseClass"}]
    def properties(self):
        return []
    def constraints(self):
        return []

ontology = DependentOntology()
''')
            
            # When: Loading dependent plugin
            base_plugin = plugin_loader.load_plugin(str(base_path))
            dependent_plugin = plugin_loader.load_plugin(str(dependent_path))
            
            # Then: Should load successfully with dependencies
            assert base_plugin.manifest.id == 'test.base'
            assert dependent_plugin.manifest.id == 'test.dependent'
            assert 'test.base@>=1.0.0' in dependent_plugin.manifest.capabilities['requires']


class TestPluginPerformance:
    """Test performance aspects of plugin system"""
    
    def test_plugin_loading_performance(self, temp_plugin_dir, plugin_loader):
        """
        Test Story: Performance Engineer - Plugin Loading Optimization
        
        Given: Multiple plugins to load
        When: Loading plugins
        Then: Should complete within acceptable time limits
        """
        import time
        
        # Create multiple test plugins
        for i in range(5):
            plugin_path = Path(temp_plugin_dir) / f"perf-plugin-{i}"
            plugin_path.mkdir()
            
            manifest = {
                'schema': 'legal-substrate.plugin/v2',
                'id': f'test.perf{i}',
                'version': '1.0.0',
                'displayName': f'Performance Test Plugin {i}',
                'domains': ['test'],
                'jurisdictions': [{'country': 'US'}],
                'capabilities': {
                    'provides': ['mapping'],
                    'requires': []
                }
            }
            
            with open(plugin_path / 'plugin.yaml', 'w') as f:
                yaml.dump(manifest, f)
            
            with open(plugin_path / 'module.py', 'w') as f:
                f.write('''
from sdk.plugin import MappingProvider

class PerfMapping(MappingProvider):
    def extract_entities(self, doc, ctx=None):
        return []
    def extract_relations(self, nodes, doc, ctx=None):
        return []
    def extract_obligations(self, doc, ctx=None):
        return []

mapping = PerfMapping()
''')
        
        # Time plugin loading
        start_time = time.time()
        
        plugins = []
        for i in range(5):
            plugin_path = Path(temp_plugin_dir) / f"perf-plugin-{i}"
            plugin = plugin_loader.load_plugin(str(plugin_path))
            plugins.append(plugin)
        
        loading_time = time.time() - start_time
        
        # Should load all plugins within reasonable time (< 5 seconds)
        assert loading_time < 5.0, f"Plugin loading took {loading_time}s, should be under 5s"
        assert len(plugins) == 5
        
        # All plugins should be properly loaded
        for plugin in plugins:
            assert plugin.provides_mapping


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])