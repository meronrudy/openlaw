"""
TDD Tests for Plugin SDK Interfaces

Following Test-Driven Development methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up and optimize

Tests cover abstract plugin interfaces for legal domain experts.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge
from sdk.plugin import (
    RawDoc, OntologyProvider, MappingProvider, RuleProvider, 
    LegalExplainer, ValidationProvider
)


class TestRawDoc:
    """Test the raw document model for plugin input"""
    
    def test_rawdoc_creation(self):
        """
        TDD: RawDoc should encapsulate input documents with metadata
        """
        doc = RawDoc(
            id="doc1",
            text="This is a legal document about employment law.",
            meta={"author": "Legal Team", "date": "2024-01-01"},
            source_info={"cite": "Contract XYZ", "url": "https://example.com/doc"}
        )
        
        assert doc.id == "doc1"
        assert "employment law" in doc.text
        assert doc.meta["author"] == "Legal Team"
        assert doc.source_info["cite"] == "Contract XYZ"
        
    def test_rawdoc_minimal_creation(self):
        """
        TDD: RawDoc should work with minimal required fields
        """
        doc = RawDoc(id="doc2", text="Short legal text")
        
        assert doc.id == "doc2"
        assert doc.text == "Short legal text"
        assert doc.meta == {}
        assert doc.source_info is None


class TestOntologyProvider:
    """Test the abstract ontology provider interface"""
    
    def test_ontology_provider_is_abstract(self):
        """
        TDD: OntologyProvider should be abstract and not instantiable
        """
        with pytest.raises(TypeError):
            OntologyProvider()
            
    def test_ontology_provider_interface(self):
        """
        TDD: OntologyProvider should define required abstract methods
        """
        # Verify the abstract methods exist
        assert hasattr(OntologyProvider, 'classes')
        assert hasattr(OntologyProvider, 'properties')
        assert hasattr(OntologyProvider, 'constraints')
        
        # Create a concrete implementation for testing
        class TestOntologyProvider(OntologyProvider):
            def classes(self) -> List[Dict[str, Any]]:
                return [
                    {"name": "Employee", "description": "A person employed by an organization"},
                    {"name": "Employer", "description": "An organization that employs people"}
                ]
                
            def properties(self) -> List[Dict[str, Any]]:
                return [
                    {"name": "employs", "domain": "Employer", "range": "Employee"},
                    {"name": "hasDisability", "domain": "Employee", "range": "Boolean"}
                ]
                
            def constraints(self) -> List[Dict[str, Any]]:
                return [
                    {"type": "required", "property": "employs", "class": "Employer"}
                ]
        
        provider = TestOntologyProvider()
        
        classes = provider.classes()
        assert len(classes) == 2
        assert classes[0]["name"] == "Employee"
        
        properties = provider.properties()
        assert len(properties) == 2
        assert properties[0]["name"] == "employs"
        
        constraints = provider.constraints()
        assert len(constraints) == 1
        assert constraints[0]["type"] == "required"


class TestMappingProvider:
    """Test the abstract mapping provider interface"""
    
    def test_mapping_provider_is_abstract(self):
        """
        TDD: MappingProvider should be abstract and not instantiable
        """
        with pytest.raises(TypeError):
            MappingProvider()
            
    def test_mapping_provider_interface(self):
        """
        TDD: MappingProvider should define extraction methods
        """
        # Verify the abstract methods exist
        assert hasattr(MappingProvider, 'extract_entities')
        assert hasattr(MappingProvider, 'extract_relations')
        assert hasattr(MappingProvider, 'extract_obligations')
        
        # Create a concrete implementation for testing
        class TestMappingProvider(MappingProvider):
            def extract_entities(self, doc: RawDoc, ctx: Optional[Context] = None) -> List[Node]:
                prov = Provenance(
                    source=[{"type": "nlp_extraction", "doc_id": doc.id}],
                    method="test.mapping.extract_entities",
                    agent="test.mapping.provider",
                    time=datetime.utcnow(),
                    confidence=0.8
                )
                
                if "employee" in doc.text.lower():
                    return [mk_node("Person", {"role": "employee"}, prov)]
                return []
                
            def extract_relations(self, nodes: List[Node], doc: RawDoc, 
                                ctx: Optional[Context] = None) -> List[Hyperedge]:
                if len(nodes) >= 2:
                    prov = Provenance(
                        source=[{"type": "nlp_extraction", "doc_id": doc.id}],
                        method="test.mapping.extract_relations",
                        agent="test.mapping.provider",
                        time=datetime.utcnow(),
                        confidence=0.7
                    )
                    return [mk_edge("knows", [nodes[0].id], [nodes[1].id], prov)]
                return []
                
            def extract_obligations(self, doc: RawDoc, 
                                  ctx: Optional[Context] = None) -> List[Hyperedge]:
                prov = Provenance(
                    source=[{"type": "nlp_extraction", "doc_id": doc.id}],
                    method="test.mapping.extract_obligations",
                    agent="test.mapping.provider",
                    time=datetime.utcnow(),
                    confidence=0.9
                )
                
                if "must" in doc.text:
                    # Create dummy nodes for the obligation
                    actor = mk_node("Actor", {"text": "employer"}, prov)
                    duty = mk_node("Duty", {"text": "reasonable accommodation"}, prov)
                    return [mk_edge("obligated", [actor.id], [duty.id], prov)]
                return []
        
        provider = TestMappingProvider()
        doc = RawDoc(id="test", text="The employee must receive accommodation")
        
        entities = provider.extract_entities(doc)
        assert len(entities) == 1
        assert entities[0].type == "Person"
        
        obligations = provider.extract_obligations(doc)
        assert len(obligations) == 1
        assert obligations[0].relation == "obligated"


class TestRuleProvider:
    """Test the abstract rule provider interface"""
    
    def test_rule_provider_is_abstract(self):
        """
        TDD: RuleProvider should be abstract and not instantiable
        """
        with pytest.raises(TypeError):
            RuleProvider()
            
    def test_rule_provider_interface(self):
        """
        TDD: RuleProvider should define rule extraction methods
        """
        # Verify the abstract methods exist
        assert hasattr(RuleProvider, 'statutory_rules')
        assert hasattr(RuleProvider, 'case_law_rules')
        assert hasattr(RuleProvider, 'exception_rules')
        
        # Create a concrete implementation for testing
        class TestRuleProvider(RuleProvider):
            def statutory_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
                prov = Provenance(
                    source=[{"type": "statute", "cite": "42 USC 12112"}],
                    method="test.rules.statutory",
                    agent="test.rule.provider",
                    time=datetime.utcnow(),
                    confidence=1.0
                )
                
                # ADA rule: qualified + disabled => accommodation required
                rule = mk_edge(
                    "implies", 
                    ["qualified_employee", "disabled"], 
                    ["accommodation_required"], 
                    prov
                )
                return [rule]
                
            def case_law_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
                prov = Provenance(
                    source=[{"type": "case", "cite": "US Airways v. Barnett"}],
                    method="test.rules.case_law",
                    agent="test.rule.provider",
                    time=datetime.utcnow(),
                    confidence=0.9
                )
                
                rule = mk_edge(
                    "implies",
                    ["seniority_system", "accommodation_request"],
                    ["undue_burden_exception"],
                    prov
                )
                return [rule]
                
            def exception_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
                prov = Provenance(
                    source=[{"type": "regulation", "cite": "29 CFR 1630.2"}],
                    method="test.rules.exceptions",
                    agent="test.rule.provider",
                    time=datetime.utcnow(),
                    confidence=0.95
                )
                
                exception = mk_edge(
                    "defeats",
                    ["undue_hardship"],
                    ["accommodation_required"],
                    prov
                )
                return [exception]
        
        provider = TestRuleProvider()
        
        statutory = provider.statutory_rules()
        assert len(statutory) == 1
        assert statutory[0].relation == "implies"
        
        case_law = provider.case_law_rules()
        assert len(case_law) == 1
        assert "undue_burden_exception" in case_law[0].heads
        
        exceptions = provider.exception_rules()
        assert len(exceptions) == 1
        assert exceptions[0].relation == "defeats"


class TestLegalExplainer:
    """Test the abstract legal explainer interface"""
    
    def test_legal_explainer_is_abstract(self):
        """
        TDD: LegalExplainer should be abstract and not instantiable
        """
        with pytest.raises(TypeError):
            LegalExplainer()
            
    def test_legal_explainer_interface(self):
        """
        TDD: LegalExplainer should define explanation methods
        """
        # Verify the abstract methods exist
        assert hasattr(LegalExplainer, 'statutory_explanation')
        assert hasattr(LegalExplainer, 'precedential_explanation')
        assert hasattr(LegalExplainer, 'counterfactual_explanation')
        
        # Create a concrete implementation for testing
        class TestLegalExplainer(LegalExplainer):
            def statutory_explanation(self, conclusion_id: str, graph) -> str:
                return f"Under 42 USC 12112, conclusion {conclusion_id} follows from statutory requirements."
                
            def precedential_explanation(self, conclusion_id: str, graph) -> str:
                return f"Based on US Airways v. Barnett, conclusion {conclusion_id} is supported by precedent."
                
            def counterfactual_explanation(self, conclusion_id: str, graph) -> str:
                return f"If key facts were different, conclusion {conclusion_id} might not hold."
        
        explainer = TestLegalExplainer()
        
        statutory_exp = explainer.statutory_explanation("conclusion1", None)
        assert "42 USC 12112" in statutory_exp
        assert "conclusion1" in statutory_exp
        
        precedential_exp = explainer.precedential_explanation("conclusion2", None)
        assert "US Airways v. Barnett" in precedential_exp
        
        counterfactual_exp = explainer.counterfactual_explanation("conclusion3", None)
        assert "different" in counterfactual_exp


class TestValidationProvider:
    """Test the abstract validation provider interface"""
    
    def test_validation_provider_is_abstract(self):
        """
        TDD: ValidationProvider should be abstract and not instantiable
        """
        with pytest.raises(TypeError):
            ValidationProvider()
            
    def test_validation_provider_interface(self):
        """
        TDD: ValidationProvider should define validation methods
        """
        # Verify the abstract methods exist
        assert hasattr(ValidationProvider, 'validate_extraction')
        assert hasattr(ValidationProvider, 'validate_reasoning')
        
        # Create a concrete implementation for testing
        class TestValidationProvider(ValidationProvider):
            def validate_extraction(self, nodes: List[Node], edges: List[Hyperedge]) -> List[str]:
                errors = []
                
                # Check that all nodes have proper provenance
                for node in nodes:
                    if node.prov.confidence < 0.5:
                        errors.append(f"Node {node.id} has low confidence: {node.prov.confidence}")
                        
                # Check that edges connect existing nodes
                node_ids = {node.id for node in nodes}
                for edge in edges:
                    for tail_id in edge.tails:
                        if tail_id not in node_ids:
                            errors.append(f"Edge {edge.id} references unknown tail: {tail_id}")
                            
                return errors
                
            def validate_reasoning(self, conclusion: Node, support: List[Hyperedge]) -> bool:
                # Simple validation: conclusion must be supported by at least one edge
                conclusion_id = conclusion.id
                for edge in support:
                    if conclusion_id in edge.heads:
                        return True
                return False
        
        validator = TestValidationProvider()
        
        # Test validation with good data
        prov = Provenance(
            source=[{"type": "test"}],
            method="test.method",
            agent="test.agent",
            time=datetime.utcnow(),
            confidence=0.8
        )
        
        node1 = mk_node("Person", {"name": "Alice"}, prov)
        node2 = mk_node("Obligation", {"type": "duty"}, prov)
        edge1 = mk_edge("has", [node1.id], [node2.id], prov)
        
        errors = validator.validate_extraction([node1, node2], [edge1])
        assert len(errors) == 0
        
        # Test reasoning validation
        is_valid = validator.validate_reasoning(node2, [edge1])
        assert is_valid is True
        
        # Test with invalid reasoning
        node3 = mk_node("Unrelated", {"name": "Bob"}, prov)
        is_invalid = validator.validate_reasoning(node3, [edge1])
        assert is_invalid is False