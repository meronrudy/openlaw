"""
Employment Law Plugin Tests

TDD test suite for employment law domain plugin demonstrating:
- ADA compliance analysis with reasonable accommodation requirements
- FLSA wage/hour compliance with overtime calculations  
- At-will employment and wrongful termination analysis
- Workers' compensation coverage and claim processing

Tests realistic legal scenarios using the hypergraph reasoning system.
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

from core.model import Node, Hyperedge, Provenance, Context, mk_node, mk_edge
from core.storage import GraphStore
from core.reasoning import RuleEngine, explain
from plugins.employment_law.plugin import EmploymentLawPlugin
from plugins.employment_law.ner import EmploymentNER
from plugins.employment_law.rules import EmploymentLawRules


class TestEmploymentNER:
    """Test employment law NER capabilities"""
    
    def test_ada_entity_extraction(self):
        """
        TDD: Should extract ADA-related entities from employment documents
        """
        ner = EmploymentNER()
        
        text = """
        Employee John Smith requested reasonable accommodation for his mobility 
        disability under the ADA. He needs ergonomic equipment and modified work 
        schedule. The employer must engage in interactive process per 42 USC 12112.
        """
        
        entities = ner.extract_entities(text)
        
        # Should identify ADA-specific entities
        entity_types = {e["type"] for e in entities}
        assert "ADA_REQUEST" in entity_types
        assert "DISABILITY" in entity_types
        assert "REASONABLE_ACCOMMODATION" in entity_types
        assert "INTERACTIVE_PROCESS" in entity_types
        
        # Should extract specific accommodations
        accommodations = [e for e in entities if e["type"] == "REASONABLE_ACCOMMODATION"]
        accommodation_text = " ".join([a["text"] for a in accommodations])
        assert "ergonomic equipment" in accommodation_text.lower()
        assert "modified work schedule" in accommodation_text.lower()
        
    def test_flsa_wage_hour_extraction(self):
        """
        TDD: Should extract FLSA wage and hour violations
        """
        ner = EmploymentNER()
        
        text = """
        Employee worked 50 hours per week at $15/hour without overtime pay.
        FLSA requires time-and-a-half for hours over 40. Manager instructed
        off-the-clock work violating 29 USC 207.
        """
        
        entities = ner.extract_entities(text)
        
        # Should identify FLSA violations
        entity_types = {e["type"] for e in entities}
        assert "FLSA_VIOLATION" in entity_types
        assert "OVERTIME" in entity_types
        assert "WAGE_RATE" in entity_types
        assert "WORK_HOURS" in entity_types
        
        # Should extract specific wage/hour data
        wage_entities = [e for e in entities if e["type"] == "WAGE_RATE"]
        assert any("$15" in e["text"] for e in wage_entities)
        
        hour_entities = [e for e in entities if e["type"] == "WORK_HOURS"]
        assert any("50 hours" in e["text"] for e in hour_entities)
        
    def test_at_will_termination_extraction(self):
        """
        TDD: Should identify at-will employment and wrongful termination issues
        """
        ner = EmploymentNER()
        
        text = """
        Employee was terminated for whistleblowing safety violations to OSHA.
        Although this is an at-will state, termination for protected activity
        violates public policy exception. Filed wrongful termination claim.
        """
        
        entities = ner.extract_entities(text)
        
        entity_types = {e["type"] for e in entities}
        assert "AT_WILL_EMPLOYMENT" in entity_types
        assert "WRONGFUL_TERMINATION" in entity_types
        assert "WHISTLEBLOWING" in entity_types
        assert "PUBLIC_POLICY_EXCEPTION" in entity_types
        
    def test_workers_comp_extraction(self):
        """
        TDD: Should extract workers' compensation related entities
        """
        ner = EmploymentNER()
        
        text = """
        Employee injured back lifting heavy boxes during work hours.
        Filed workers' compensation claim for medical treatment and
        lost wages. Employer cannot retaliate per state workers' comp statute.
        """
        
        entities = ner.extract_entities(text)
        
        entity_types = {e["type"] for e in entities}
        assert "WORK_INJURY" in entity_types
        assert "WORKERS_COMP_CLAIM" in entity_types
        assert "MEDICAL_TREATMENT" in entity_types
        assert "LOST_WAGES" in entity_types
        assert "RETALIATION" in entity_types


class TestEmploymentLawRules:
    """Test employment law rule implementation"""
    
    def test_ada_reasonable_accommodation_rules(self):
        """
        TDD: Should implement ADA reasonable accommodation analysis rules
        """
        rules = EmploymentLawRules()
        legal_rules = rules.get_ada_rules()
        
        # Should have key ADA rules
        rule_ids = {rule.id for rule in legal_rules}
        assert "ada_accommodation_required" in rule_ids
        assert "ada_undue_hardship_defense" in rule_ids
        assert "ada_interactive_process" in rule_ids
        
        # Rules should have proper authority
        accommodation_rule = next(r for r in legal_rules if r.id == "ada_accommodation_required")
        assert "42 U.S.C. § 12112" in accommodation_rule.authority
        assert accommodation_rule.rule_type == "statutory"
        
    def test_flsa_overtime_rules(self):
        """
        TDD: Should implement FLSA overtime calculation rules
        """
        rules = EmploymentLawRules()
        legal_rules = rules.get_flsa_rules()
        
        rule_ids = {rule.id for rule in legal_rules}
        assert "flsa_overtime_required" in rule_ids
        assert "flsa_exempt_employee" in rule_ids
        assert "flsa_time_and_half" in rule_ids
        
        # Should have proper FLSA authority
        overtime_rule = next(r for r in legal_rules if r.id == "flsa_overtime_required")
        assert "29 U.S.C. § 207" in overtime_rule.authority
        
    def test_at_will_exception_rules(self):
        """
        TDD: Should implement at-will employment exception rules
        """
        rules = EmploymentLawRules()
        legal_rules = rules.get_at_will_rules()
        
        rule_ids = {rule.id for rule in legal_rules}
        assert "at_will_general_rule" in rule_ids
        assert "public_policy_exception" in rule_ids
        assert "implied_contract_exception" in rule_ids
        
    def test_workers_comp_rules(self):
        """
        TDD: Should implement workers' compensation rules
        """
        rules = EmploymentLawRules()
        legal_rules = rules.get_workers_comp_rules()
        
        rule_ids = {rule.id for rule in legal_rules}
        assert "workers_comp_coverage" in rule_ids
        assert "course_of_employment" in rule_ids
        assert "workers_comp_exclusivity" in rule_ids


class TestEmploymentLawPlugin:
    """Test employment law plugin integration"""
    
    def test_plugin_initialization(self):
        """
        TDD: Should initialize employment law plugin with all components
        """
        plugin = EmploymentLawPlugin()
        
        assert plugin.name == "Employment Law"
        assert plugin.version == "1.0.0"
        assert plugin.description is not None
        
        # Should have all required providers
        assert hasattr(plugin, 'ner')
        assert hasattr(plugin, 'rules')
        
    def test_ada_accommodation_analysis(self):
        """
        TDD: Should analyze ADA reasonable accommodation scenario
        """
        plugin = EmploymentLawPlugin()
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US", law_type="employment")
        
        # Load plugin rules into graph
        plugin.load_rules(graph, context)
        
        # Add facts from ADA scenario
        prov = Provenance(
            source=[{"type": "case_file", "id": "ADA_001"}],
            method="legal.analysis",
            agent="employment.plugin",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        # Employee has disability
        disability_fact = mk_node("Fact", {
            "statement": "employee_has_disability",
            "person": "John Smith",
            "disability_type": "mobility"
        }, prov)
        graph.add_node(disability_fact)
        
        # Employee can perform essential functions with accommodation
        essential_functions_fact = mk_node("Fact", {
            "statement": "can_perform_essential_functions_with_accommodation",
            "person": "John Smith",
            "accommodation": "ergonomic equipment"
        }, prov)
        graph.add_node(essential_functions_fact)
        
        # Run reasoning
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        # Should derive accommodation requirement
        statements = {f.data.get("statement") for f in derived_facts}
        assert "reasonable_accommodation_required" in statements
        
    def test_flsa_overtime_analysis(self):
        """
        TDD: Should analyze FLSA overtime violation scenario
        """
        plugin = EmploymentLawPlugin()
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US", law_type="employment")
        
        plugin.load_rules(graph, context)
        
        prov = Provenance(
            source=[{"type": "timesheet", "id": "FLSA_001"}],
            method="wage.analysis",
            agent="employment.plugin",
            time=datetime.utcnow(),
            confidence=0.95
        )
        
        # Employee worked over 40 hours
        overtime_hours_fact = mk_node("Fact", {
            "statement": "worked_over_40_hours",
            "person": "Jane Doe",
            "hours_worked": 50,
            "week_period": "2024-W01"
        }, prov)
        graph.add_node(overtime_hours_fact)
        
        # Employee is non-exempt
        non_exempt_fact = mk_node("Fact", {
            "statement": "employee_non_exempt",
            "person": "Jane Doe",
            "classification": "hourly"
        }, prov)
        graph.add_node(non_exempt_fact)
        
        # Run reasoning
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        # Should derive overtime pay requirement
        statements = {f.data.get("statement") for f in derived_facts}
        assert "overtime_pay_required" in statements
        
    def test_wrongful_termination_analysis(self):
        """
        TDD: Should analyze wrongful termination claim
        """
        plugin = EmploymentLawPlugin()
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="California", law_type="employment")
        
        plugin.load_rules(graph, context)
        
        prov = Provenance(
            source=[{"type": "hr_record", "id": "TERM_001"}],
            method="termination.analysis",
            agent="employment.plugin",
            time=datetime.utcnow(),
            confidence=0.85
        )
        
        # At-will employment
        at_will_fact = mk_node("Fact", {
            "statement": "at_will_employment",
            "person": "Bob Wilson",
            "state": "California"
        }, prov)
        graph.add_node(at_will_fact)
        
        # Terminated for protected activity
        protected_activity_fact = mk_node("Fact", {
            "statement": "terminated_for_protected_activity",
            "person": "Bob Wilson",
            "activity": "whistleblowing_safety_violations"
        }, prov)
        graph.add_node(protected_activity_fact)
        
        # Run reasoning
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        # Should derive wrongful termination claim
        statements = {f.data.get("statement") for f in derived_facts}
        assert "wrongful_termination_claim_viable" in statements
        
    def test_explanation_generation(self):
        """
        TDD: Should generate detailed explanations for employment law conclusions
        """
        plugin = EmploymentLawPlugin()
        graph = GraphStore(":memory:")
        context = Context(jurisdiction="US", law_type="employment")
        
        plugin.load_rules(graph, context)
        
        # Set up simple ADA scenario
        prov = Provenance(
            source=[{"type": "case_file", "id": "EXPLAIN_001"}],
            method="legal.analysis",
            agent="employment.plugin",
            time=datetime.utcnow(),
            confidence=0.9
        )
        
        disability_fact = mk_node("Fact", {
            "statement": "employee_has_disability",
            "details": "mobility impairment"
        }, prov)
        graph.add_node(disability_fact)
        
        accommodation_fact = mk_node("Fact", {
            "statement": "can_perform_essential_functions_with_accommodation",
            "accommodation": "wheelchair accessible workspace"
        }, prov)
        graph.add_node(accommodation_fact)
        
        # Run reasoning to get conclusion
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        # Find accommodation requirement conclusion
        accommodation_conclusion = None
        for fact in derived_facts:
            if fact.data.get("statement") == "reasonable_accommodation_required":
                accommodation_conclusion = fact
                break
        
        assert accommodation_conclusion is not None
        
        # Generate explanation
        explanation = explain(graph, accommodation_conclusion.id)
        
        # Should have structured explanation
        assert "conclusion" in explanation
        assert "supports" in explanation
        assert "confidence" in explanation
        assert len(explanation["supports"]) >= 1
        
        # Should reference ADA authority
        rule_authorities = []
        for support in explanation["supports"]:
            rule_authorities.append(support["rule"]["authority"])
        
        ada_authority_found = any("42 U.S.C." in auth for auth in rule_authorities)
        assert ada_authority_found