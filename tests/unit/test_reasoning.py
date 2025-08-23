"""
TDD Tests for Forward-Chaining Rule Engine

Following Test-Driven Development methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up and optimize

Tests cover forward-chaining reasoning, conflict resolution, and explanation generation.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge
from core.storage import GraphStore
from core.reasoning import RuleEngine, ConflictResolver, explain
from core.rules import LegalRule


class TestRuleEngine:
    """Test the forward-chaining rule engine"""
    
    def test_rule_engine_initialization(self):
        """
        TDD: RuleEngine should initialize with graph and context
        """
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US", law_type="statute")
        
        engine = RuleEngine(graph, context)
        
        assert engine.graph == graph
        assert engine.context == context
        assert engine.max_iterations > 0
        assert engine.applied_rules == set()
        
    def test_simple_forward_chaining(self):
        """
        TDD: Should perform basic forward chaining with modus ponens
        """
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US")
        
        prov = Provenance(
            source=[{"type": "test", "rule": "modus_ponens"}],
            method="test.reasoning",
            agent="test.engine",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        # Add premise: "P"
        premise = mk_node("Fact", {"statement": "P"}, prov)
        graph.add_node(premise)
        
        # Add rule: "P → Q"
        conclusion_q = mk_node("Fact", {"statement": "Q"}, prov)
        rule = mk_edge("implies", [premise.id], [conclusion_q.id], prov,
                      qualifiers={"rule_type": "implication"})
        graph.add_edge(rule)
        
        # Run forward chaining
        engine = RuleEngine(graph, context)
        new_facts = engine.forward_chain()
        
        # Should derive Q
        assert len(new_facts) >= 1
        derived_q = next((f for f in new_facts if f.data.get("statement") == "Q"), None)
        assert derived_q is not None
        assert derived_q.type == "Fact"
        
    def test_complex_rule_chaining(self):
        """
        TDD: Should handle complex multi-step reasoning chains
        """
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US")
        
        prov = Provenance(
            source=[{"type": "test", "rule": "complex_chain"}],
            method="test.reasoning",
            agent="test.engine",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # P1 ∧ P2 → R1
        # R1 ∧ P3 → R2
        # R2 → CONCLUSION
        
        # Add premises
        p1 = mk_node("Fact", {"statement": "P1"}, prov)
        p2 = mk_node("Fact", {"statement": "P2"}, prov)
        p3 = mk_node("Fact", {"statement": "P3"}, prov)
        
        graph.add_node(p1)
        graph.add_node(p2)
        graph.add_node(p3)
        
        # Add intermediate conclusions
        r1 = mk_node("Fact", {"statement": "R1"}, prov)
        r2 = mk_node("Fact", {"statement": "R2"}, prov)
        conclusion = mk_node("Conclusion", {"statement": "FINAL"}, prov)
        
        # Add rules
        rule1 = mk_edge("implies", [p1.id, p2.id], [r1.id], prov,
                       qualifiers={"rule_id": "rule1"})
        rule2 = mk_edge("implies", [r1.id, p3.id], [r2.id], prov,
                       qualifiers={"rule_id": "rule2"})
        rule3 = mk_edge("implies", [r2.id], [conclusion.id], prov,
                       qualifiers={"rule_id": "rule3"})
        
        graph.add_edge(rule1)
        graph.add_edge(rule2)
        graph.add_edge(rule3)
        
        # Run forward chaining
        engine = RuleEngine(graph, context)
        new_facts = engine.forward_chain()
        
        # Should derive all intermediate steps and final conclusion
        derived_statements = {f.data.get("statement") for f in new_facts}
        assert "R1" in derived_statements
        assert "R2" in derived_statements
        assert "FINAL" in derived_statements
        
    def test_rule_application_tracking(self):
        """
        TDD: Should track which rules have been applied to prevent loops
        """
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US")
        
        prov = Provenance(
            source=[{"type": "test", "rule": "tracking"}],
            method="test.reasoning",
            agent="test.engine",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        # Create a simple rule P → Q
        premise = mk_node("Fact", {"statement": "P"}, prov)
        conclusion = mk_node("Fact", {"statement": "Q"}, prov)
        
        graph.add_node(premise)
        
        rule = mk_edge("implies", [premise.id], [conclusion.id], prov,
                      qualifiers={"rule_id": "test_rule_1"})
        graph.add_edge(rule)
        
        engine = RuleEngine(graph, context)
        
        # First application should work
        new_facts = engine.forward_chain()
        assert len(new_facts) >= 1
        
        # Rule should be marked as applied
        assert rule.id in engine.applied_rules
        
        # Second application should not re-derive the same fact
        new_facts_2 = engine.forward_chain()
        assert len(new_facts_2) == 0  # No new facts
        
    def test_confidence_propagation(self):
        """
        TDD: Should propagate confidence scores through reasoning chain
        """
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US")
        
        # Create provenance with different confidence levels
        high_conf_prov = Provenance(
            source=[{"type": "statute", "cite": "42 USC 1981"}],
            method="statutory.extraction",
            agent="legal.expert",
            time=datetime.utcnow(),
            confidence=0.95
        )
        
        low_conf_prov = Provenance(
            source=[{"type": "case", "cite": "Uncertain v. Case"}],
            method="nlp.extraction",
            agent="nlp.model",
            time=datetime.utcnow(),
            confidence=0.7
        )
        
        # High confidence premise
        premise = mk_node("Fact", {"statement": "HighConfidence"}, high_conf_prov)
        graph.add_node(premise)
        
        # Low confidence rule
        conclusion = mk_node("Fact", {"statement": "Derived"}, low_conf_prov)
        rule = mk_edge("implies", [premise.id], [conclusion.id], low_conf_prov)
        graph.add_edge(rule)
        
        engine = RuleEngine(graph, context)
        new_facts = engine.forward_chain()
        
        # Derived fact should have confidence influenced by weakest link
        derived_fact = next((f for f in new_facts if f.data.get("statement") == "Derived"), None)
        assert derived_fact is not None
        assert derived_fact.prov.confidence <= 0.7  # Should not exceed rule confidence
        
    def test_contextual_rule_application(self):
        """
        TDD: Should only apply rules that are valid in the current context
        """
        graph = GraphStore(":memory:")
        us_context = Context(jurisdiction="US", law_type="statute")
        uk_context = Context(jurisdiction="UK", law_type="statute")
        
        prov = Provenance(
            source=[{"type": "test", "rule": "contextual"}],
            method="test.reasoning",
            agent="test.engine",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        # Add premise
        premise = mk_node("Fact", {"statement": "P"}, prov)
        graph.add_node(premise)
        
        # Add US-specific rule
        us_conclusion = mk_node("Fact", {"statement": "US_RESULT"}, prov)
        us_rule = mk_edge("implies", [premise.id], [us_conclusion.id], prov,
                         ctx=us_context,
                         qualifiers={"jurisdiction": "US"})
        graph.add_edge(us_rule)
        
        # Add UK-specific rule
        uk_conclusion = mk_node("Fact", {"statement": "UK_RESULT"}, prov)
        uk_rule = mk_edge("implies", [premise.id], [uk_conclusion.id], prov,
                         ctx=uk_context,
                         qualifiers={"jurisdiction": "UK"})
        graph.add_edge(uk_rule)
        
        # Test with US context
        us_engine = RuleEngine(graph, us_context)
        us_facts = us_engine.forward_chain()
        us_statements = {f.data.get("statement") for f in us_facts}
        
        assert "US_RESULT" in us_statements
        assert "UK_RESULT" not in us_statements


class TestConflictResolver:
    """Test rule conflict resolution"""
    
    def test_conflict_resolver_initialization(self):
        """
        TDD: ConflictResolver should initialize with resolution strategies
        """
        resolver = ConflictResolver()
        
        assert resolver.strategies is not None
        assert len(resolver.strategies) > 0
        assert "authority_hierarchy" in resolver.strategies
        assert "specificity" in resolver.strategies
        
    def test_authority_hierarchy_resolution(self):
        """
        TDD: Should resolve conflicts using authority hierarchy (federal > state > local)
        """
        resolver = ConflictResolver()
        
        federal_rule = LegalRule(
            id="federal_rule",
            rule_type="statutory",
            priority=100,
            authority="42 U.S.C. § 1981",
            jurisdiction=Context(authority_level="federal"),
            premises=[],
            conclusions=[]
        )
        
        state_rule = LegalRule(
            id="state_rule",
            rule_type="statutory",
            priority=100,
            authority="State Code § 100",
            jurisdiction=Context(authority_level="state"),
            premises=[],
            conclusions=[]
        )
        
        resolved = resolver.resolve_conflicts([federal_rule, state_rule], [])
        
        # Should prefer federal rule
        assert len(resolved) == 1
        assert resolved[0].id == "federal_rule"
        
    def test_specificity_resolution(self):
        """
        TDD: Should resolve conflicts by preferring more specific rules
        """
        resolver = ConflictResolver()
        
        general_rule = LegalRule(
            id="general_rule",
            rule_type="statutory",
            priority=100,
            authority="General Statute § 1",
            jurisdiction=Context(law_type="statute"),
            premises=["general_condition"],
            conclusions=["general_result"]
        )
        
        specific_rule = LegalRule(
            id="specific_rule",
            rule_type="statutory",
            priority=100,
            authority="Specific Statute § 2",
            jurisdiction=Context(law_type="statute"),
            premises=["general_condition", "specific_condition"],
            conclusions=["specific_result"]
        )
        
        # More premises = more specific
        resolved = resolver.resolve_conflicts([general_rule, specific_rule], [])
        
        # Should prefer more specific rule
        assert len(resolved) == 1
        assert resolved[0].id == "specific_rule"
        
    def test_temporal_resolution(self):
        """
        TDD: Should resolve conflicts by preferring more recent rules
        """
        resolver = ConflictResolver()
        
        old_rule = LegalRule(
            id="old_rule",
            rule_type="statutory",
            priority=100,
            authority="Old Act § 1",
            jurisdiction=Context(valid_from=datetime(2020, 1, 1)),
            premises=[],
            conclusions=[]
        )
        
        new_rule = LegalRule(
            id="new_rule",
            rule_type="statutory",
            priority=100,
            authority="New Act § 1",
            jurisdiction=Context(valid_from=datetime(2024, 1, 1)),
            premises=[],
            conclusions=[]
        )
        
        resolved = resolver.resolve_conflicts([old_rule, new_rule], [])
        
        # Should prefer newer rule
        assert len(resolved) == 1
        assert resolved[0].id == "new_rule"


class TestExplanationGeneration:
    """Test explanation generation for reasoning chains"""
    
    def test_basic_explanation_structure(self):
        """
        TDD: Should generate structured explanations with premises, rules, and conclusions
        """
        graph = GraphStore(":memory:")
        
        prov = Provenance(
            source=[{"type": "test", "cite": "Test v. Case"}],
            method="test.manual",
            agent="test_user",
            time=datetime.utcnow(),
            confidence=1.0
        )
        
        # Create reasoning chain
        premise = mk_node("Fact", {"statement": "test_premise"}, prov)
        conclusion = mk_node("Obligation", {"statement": "test_conclusion"}, prov)
        
        graph.add_node(premise)
        graph.add_node(conclusion)
        
        # Add justification edge
        justification = mk_edge("implies", [premise.id], [conclusion.id], prov,
                               qualifiers={
                                   "rule_id": "test_rule", 
                                   "authority": "Test Statute § 1",
                                   "rule_text": "If premise then conclusion"
                               })
        graph.add_edge(justification)
        
        # Generate explanation
        explanation = explain(graph, conclusion.id)
        
        assert "conclusion" in explanation
        assert "supports" in explanation
        assert len(explanation["supports"]) > 0
        
        support = explanation["supports"][0]
        assert "premises" in support
        assert "rule" in support
        assert support["rule"]["authority"] == "Test Statute § 1"
        assert len(support["premises"]) > 0
        
    def test_multi_step_explanation(self):
        """
        TDD: Should generate explanations for multi-step reasoning chains
        """
        graph = GraphStore(":memory:")
        
        prov = Provenance(
            source=[{"type": "test", "cite": "Multi v. Step"}],
            method="test.complex",
            agent="test_user",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Create chain: P1 → R1 → CONCLUSION
        p1 = mk_node("Fact", {"statement": "P1"}, prov)
        r1 = mk_node("Fact", {"statement": "R1"}, prov) 
        conclusion = mk_node("Conclusion", {"statement": "FINAL"}, prov)
        
        graph.add_node(p1)
        graph.add_node(r1)
        graph.add_node(conclusion)
        
        # Add reasoning steps
        step1 = mk_edge("implies", [p1.id], [r1.id], prov,
                       qualifiers={"rule_id": "step1", "authority": "Rule 1"})
        step2 = mk_edge("implies", [r1.id], [conclusion.id], prov,
                       qualifiers={"rule_id": "step2", "authority": "Rule 2"})
        
        graph.add_edge(step1)
        graph.add_edge(step2)
        
        # Generate explanation
        explanation = explain(graph, conclusion.id)
        
        # Should trace back through the entire reasoning chain
        assert len(explanation["supports"]) >= 1
        
        # Should be able to trace back to original premises
        all_premises = []
        for support in explanation["supports"]:
            all_premises.extend(support["premises"])
            
        premise_statements = {p["statement"] for p in all_premises}
        assert "P1" in premise_statements
        
    def test_explanation_confidence_tracking(self):
        """
        TDD: Should track confidence scores throughout explanation chain
        """
        graph = GraphStore(":memory:")
        
        high_conf_prov = Provenance(
            source=[{"type": "statute", "cite": "High Conf § 1"}],
            method="statutory.extraction",
            agent="legal.expert",
            time=datetime.utcnow(),
            confidence=0.95
        )
        
        low_conf_prov = Provenance(
            source=[{"type": "case", "cite": "Low Conf v. Case"}],
            method="nlp.extraction",
            agent="nlp.model",
            time=datetime.utcnow(),
            confidence=0.6
        )
        
        # High confidence premise
        premise = mk_node("Fact", {"statement": "reliable_fact"}, high_conf_prov)
        conclusion = mk_node("Conclusion", {"statement": "uncertain_conclusion"}, low_conf_prov)
        
        graph.add_node(premise)
        graph.add_node(conclusion)
        
        # Low confidence rule
        rule = mk_edge("implies", [premise.id], [conclusion.id], low_conf_prov,
                      qualifiers={"authority": "Uncertain Rule"})
        graph.add_edge(rule)
        
        explanation = explain(graph, conclusion.id)
        
        # Should include confidence information
        assert "confidence" in explanation
        assert explanation["confidence"] <= 0.6  # Limited by weakest link
        
        # Individual supports should also have confidence
        for support in explanation["supports"]:
            assert "confidence" in support


class TestLegalRule:
    """Test the LegalRule data structure"""
    
    def test_legal_rule_creation(self):
        """
        TDD: LegalRule should encapsulate rule metadata and logic
        """
        rule = LegalRule(
            id="ada_accommodation_rule",
            rule_type="statutory",
            priority=100,
            authority="42 U.S.C. § 12112(b)(5)(A)",
            jurisdiction=Context(jurisdiction="US", authority_level="federal"),
            premises=["qualified_employee", "disability", "reasonable_request"],
            conclusions=["accommodation_required"]
        )
        
        assert rule.id == "ada_accommodation_rule"
        assert rule.rule_type == "statutory"
        assert rule.priority == 100
        assert "12112" in rule.authority
        assert len(rule.premises) == 3
        assert len(rule.conclusions) == 1
        
    def test_legal_rule_to_hyperedge(self):
        """
        TDD: LegalRule should convert to Hyperedge for graph storage
        """
        rule = LegalRule(
            id="test_rule",
            rule_type="statutory",
            priority=100,
            authority="Test Statute § 1",
            jurisdiction=Context(jurisdiction="US"),
            premises=["P1", "P2"],
            conclusions=["C1"]
        )
        
        edge = rule.to_hyperedge()
        
        assert edge.relation == "implies"
        assert edge.tails == ["P1", "P2"]
        assert edge.heads == ["C1"]
        assert edge.qualifiers["rule_id"] == "test_rule"
        assert edge.qualifiers["authority"] == "Test Statute § 1"
        assert edge.prov.source[0]["authority"] == "Test Statute § 1"
        
    def test_rule_applicability_check(self):
        """
        TDD: LegalRule should check if it's applicable in given context
        """
        us_rule = LegalRule(
            id="us_rule",
            rule_type="statutory",
            priority=100,
            authority="US Code § 1",
            jurisdiction=Context(jurisdiction="US"),
            premises=[],
            conclusions=[]
        )
        
        ca_rule = LegalRule(
            id="ca_rule",
            rule_type="statutory",
            priority=100,
            authority="CA Code § 1",
            jurisdiction=Context(jurisdiction="CA"),
            premises=[],
            conclusions=[]
        )
        
        us_context = Context(jurisdiction="US")
        ca_context = Context(jurisdiction="CA")
        
        assert us_rule.is_applicable_in(us_context) is True
        assert us_rule.is_applicable_in(ca_context) is False
        assert ca_rule.is_applicable_in(ca_context) is True
        assert ca_rule.is_applicable_in(us_context) is False