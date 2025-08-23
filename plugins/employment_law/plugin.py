"""
Employment Law Plugin Implementation

Main plugin class that integrates employment law NER, rules, and reasoning
for comprehensive employment law analysis including ADA, FLSA, at-will
employment, and workers' compensation scenarios.

Implements the plugin SDK interfaces for seamless integration with the
legal hypergraph reasoning system.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from core.model import Node, Hyperedge, Context, mk_node, mk_edge, Provenance
from core.storage import GraphStore
from core.reasoning import RuleEngine
from core.rules import LegalRule
from sdk.plugin import OntologyProvider, RuleProvider, LegalExplainer
from .ner import EmploymentNER
from .rules import EmploymentLawRules


class EmploymentLawPlugin:
    """
    Employment Law Domain Plugin
    
    Provides comprehensive employment law analysis capabilities including:
    - Specialized NER for employment law documents
    - Legal rules for ADA, FLSA, at-will employment, workers' compensation
    - Integration with hypergraph reasoning system
    """
    
    def __init__(self):
        """Initialize employment law plugin"""
        self.name = "Employment Law"
        self.version = "1.0.0"
        self.description = "Comprehensive employment law analysis with ADA, FLSA, at-will employment, and workers' compensation support"
        
        # Initialize components
        self.ner = EmploymentNER()
        self.rules = EmploymentLawRules()
        
    def load_rules(self, graph: GraphStore, context: Context) -> None:
        """
        Load employment law rules into the hypergraph
        
        Args:
            graph: Graph store to load rules into
            context: Legal context for rule application
        """
        # Get all employment law rules
        employment_rules = self.rules.get_all_rules()
        
        # Convert legal rules to hyperedges and add to graph
        for legal_rule in employment_rules:
            # Convert to hyperedge (LegalRule creates its own provenance)
            rule_edge = legal_rule.to_hyperedge()
            graph.add_edge(rule_edge)
    
    def analyze_document(self, text: str, context: Context) -> Dict[str, Any]:
        """
        Analyze employment law document using NER and reasoning
        
        Args:
            text: Document text to analyze
            context: Legal context for analysis
            
        Returns:
            Analysis results with entities, facts, and conclusions
        """
        # Extract entities using employment law NER
        entities = self.ner.extract_entities(text)
        legal_citations = self.ner.extract_legal_citations(text)
        
        # Create graph for analysis
        graph = GraphStore(":memory:")
        
        # Load employment law rules
        self.load_rules(graph, context)
        
        # Convert entities to facts in the graph
        document_prov = Provenance(
            source=[{
                "type": "document_analysis",
                "method": "employment_ner",
                "text_length": len(text)
            }],
            method="nlp.extraction",
            agent="employment.plugin",
            time=datetime.utcnow(),
            confidence=0.85
        )
        
        facts = self._entities_to_facts(entities, document_prov)
        
        # Add facts to graph
        for fact in facts:
            graph.add_node(fact)
        
        # Run reasoning
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        return {
            "entities": entities,
            "citations": legal_citations,
            "original_facts": [f.data for f in facts],
            "derived_facts": [f.data for f in derived_facts],
            "conclusions": self._extract_conclusions(derived_facts),
            "context": context.model_dump() if context else None
        }
    
    def _entities_to_facts(self, entities: List[Dict[str, Any]], prov: Provenance) -> List[Node]:
        """
        Convert NER entities to graph facts
        
        Args:
            entities: Extracted entities from NER
            prov: Provenance for the facts
            
        Returns:
            List of fact nodes
        """
        facts = []
        
        # Group entities by type to create meaningful facts
        entity_groups = {}
        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(entity)
        
        # Convert entity groups to facts based on employment law patterns
        for entity_type, group_entities in entity_groups.items():
            if entity_type == "DISABILITY":
                # Create disability fact
                disability_text = " ".join([e["text"] for e in group_entities])
                fact = mk_node("Fact", {
                    "statement": "employee_has_disability",
                    "disability_details": disability_text,
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "REASONABLE_ACCOMMODATION":
                # Create accommodation capability fact
                accommodation_text = " ".join([e["text"] for e in group_entities])
                fact = mk_node("Fact", {
                    "statement": "can_perform_essential_functions_with_accommodation",
                    "accommodation": accommodation_text,
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "WORK_HOURS":
                # Analyze work hours for FLSA compliance
                for entity in group_entities:
                    # Extract hour numbers from text
                    hour_text = entity["text"].lower()
                    if "50 hours" in hour_text or "over 40" in hour_text:
                        fact = mk_node("Fact", {
                            "statement": "worked_over_40_hours",
                            "hours_details": entity["text"],
                            "entity_type": entity_type
                        }, prov)
                        facts.append(fact)
                        
            elif entity_type == "FLSA_VIOLATION":
                # Create non-exempt employee assumption
                fact = mk_node("Fact", {
                    "statement": "employee_non_exempt",
                    "violation_details": " ".join([e["text"] for e in group_entities]),
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "AT_WILL_EMPLOYMENT":
                fact = mk_node("Fact", {
                    "statement": "at_will_employment",
                    "details": " ".join([e["text"] for e in group_entities]),
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "WHISTLEBLOWING":
                fact = mk_node("Fact", {
                    "statement": "terminated_for_protected_activity",
                    "activity": "whistleblowing_safety_violations",
                    "details": " ".join([e["text"] for e in group_entities]),
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "WORK_INJURY":
                fact = mk_node("Fact", {
                    "statement": "injury_in_course_of_employment",
                    "injury_details": " ".join([e["text"] for e in group_entities]),
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
                
            elif entity_type == "WORKERS_COMP_CLAIM":
                fact = mk_node("Fact", {
                    "statement": "filed_workers_comp_claim",
                    "claim_details": " ".join([e["text"] for e in group_entities]),
                    "entity_type": entity_type
                }, prov)
                facts.append(fact)
        
        return facts
    
    def _extract_conclusions(self, derived_facts: List[Node]) -> List[Dict[str, Any]]:
        """
        Extract high-level conclusions from derived facts
        
        Args:
            derived_facts: Facts derived from reasoning
            
        Returns:
            List of legal conclusions with explanations
        """
        conclusions = []
        
        # Look for key conclusion patterns
        for fact in derived_facts:
            statement = fact.data.get("statement", "")
            
            if statement == "reasonable_accommodation_required":
                conclusions.append({
                    "type": "ADA_VIOLATION",
                    "conclusion": "Employer may be required to provide reasonable accommodation",
                    "legal_basis": "42 U.S.C. § 12112(b)(5)(A)",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
                
            elif statement == "overtime_pay_required":
                conclusions.append({
                    "type": "FLSA_VIOLATION", 
                    "conclusion": "Employee entitled to overtime compensation",
                    "legal_basis": "29 U.S.C. § 207(a)(1)",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
                
            elif statement == "wrongful_termination_claim_viable":
                conclusions.append({
                    "type": "WRONGFUL_TERMINATION",
                    "conclusion": "Potential wrongful termination claim under public policy exception",
                    "legal_basis": "State common law public policy exception",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
                
            elif statement == "workers_comp_benefits_available":
                conclusions.append({
                    "type": "WORKERS_COMPENSATION",
                    "conclusion": "Employee may be entitled to workers' compensation benefits",
                    "legal_basis": "State workers' compensation statute",
                    "confidence": fact.prov.confidence,
                    "fact_id": fact.id
                })
        
        return conclusions
    
    def get_supported_domains(self) -> List[str]:
        """
        Get list of supported employment law domains
        
        Returns:
            List of supported domain names
        """
        return ["ada", "flsa", "at_will", "workers_comp"]
    
    def explain_conclusion(self, graph: GraphStore, conclusion_id: str) -> Dict[str, Any]:
        """
        Generate detailed explanation for a legal conclusion
        
        Args:
            graph: Graph containing the reasoning chain
            conclusion_id: ID of conclusion node to explain
            
        Returns:
            Structured explanation with legal reasoning chain
        """
        from core.reasoning import explain
        
        # Get basic explanation
        explanation = explain(graph, conclusion_id)
        
        # Enhance with employment law specific information
        enhanced_explanation = {
            **explanation,
            "domain": "employment_law",
            "plugin_version": self.version,
            "legal_analysis": self._enhance_legal_analysis(explanation)
        }
        
        return enhanced_explanation
    
    def _enhance_legal_analysis(self, explanation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance explanation with employment law specific analysis
        
        Args:
            explanation: Basic explanation structure
            
        Returns:
            Enhanced legal analysis
        """
        analysis = {
            "applicable_statutes": [],
            "key_requirements": [],
            "potential_defenses": [],
            "next_steps": []
        }
        
        # Extract legal authorities from explanation
        for support in explanation.get("supports", []):
            authority = support.get("rule", {}).get("authority", "")
            
            if "42 U.S.C." in authority:
                analysis["applicable_statutes"].append("Americans with Disabilities Act (ADA)")
                analysis["key_requirements"].append("Interactive process with employee")
                analysis["potential_defenses"].append("Undue hardship defense")
                analysis["next_steps"].append("Engage in interactive process to identify accommodation")
                
            elif "29 U.S.C." in authority:
                analysis["applicable_statutes"].append("Fair Labor Standards Act (FLSA)")
                analysis["key_requirements"].append("Time and one-half for overtime hours")
                analysis["potential_defenses"].append("Employee exempt classification")
                analysis["next_steps"].append("Calculate overtime compensation owed")
                
        # Remove duplicates
        for key in analysis:
            analysis[key] = list(set(analysis[key]))
            
        return analysis