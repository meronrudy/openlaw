"""
End-to-End Tests: Legal Document Analysis Workflow

Tests the complete workflow from document upload through legal analysis
to explanation generation, covering user stories for legal researchers
and practitioners.
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from core.system import LegalHypergraphSystem
from core.model import Node, Hyperedge, Context, Provenance
from core.storage import GraphStore
from sdk.plugin import RawDoc
from plugins.employment_us.module import mapping, rules, explainer
from tests.fixtures.legal_documents import TestDocuments
from tests.helpers.legal_assertions import LegalAssertions


class TestLegalDocumentAnalysis:
    """Test complete legal document analysis workflows"""
    
    @pytest.fixture(scope="class")
    async def system(self):
        """Initialize legal hypergraph system with employment plugin"""
        system = LegalHypergraphSystem(
            storage_config={'path': ':memory:'},
            plugin_dirs=['plugins']
        )
        await system.initialize()
        await system.load_plugin('employment-us')
        yield system
        await system.shutdown()
    
    @pytest.fixture
    def legal_context(self):
        """Standard US legal context for testing"""
        return Context(
            jurisdiction="US",
            law_type="statute",
            authority_level="federal"
        )
    
    @pytest.fixture
    def legal_assertions(self):
        """Helper for legal-specific assertions"""
        return LegalAssertions()

    class TestADAAnalysis:
        """Test ADA reasonable accommodation analysis workflow"""
        
        async def test_ada_accommodation_complete_workflow(self, system, legal_context, legal_assertions):
            """
            Test Story: Legal Researcher - Document Analysis for ADA Compliance
            
            Given: A document describing an ADA accommodation scenario
            When: System analyzes the document and applies legal rules
            Then: System should identify legal obligations with complete provenance
            """
            # Given: ADA accommodation request document
            document = RawDoc(
                id="ada-test-001",
                text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
                meta={"type": "employment_scenario", "domain": "ada"}
            )
            
            # When: Analyzing the document
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should extract all required entities
            entities = analysis_result['entities']
            assert len(entities) >= 4, "Should extract at least 4 entities (Employee, Employer, Disability, Request)"
            
            entity_types = {entity.type for entity in entities}
            legal_assertions.assert_contains_entity_types(entity_types, [
                'Employee', 'Employer', 'Disability', 'AccommodationRequest'
            ])
            
            # And: Should derive ADA accommodation obligation
            obligations = analysis_result['obligations']
            ada_obligations = [o for o in obligations if 'accommodation' in str(o.data).lower()]
            assert len(ada_obligations) > 0, "Should derive ADA accommodation obligation"
            
            # And: Obligation should have proper provenance
            obligation = ada_obligations[0]
            legal_assertions.assert_valid_provenance(obligation.prov)
            legal_assertions.assert_contains_legal_authority(obligation.prov.source, "42 U.S.C.")
            
            # And: Should generate explanation
            explanation = await system.explain_conclusion(obligation.id)
            assert "ADA" in explanation or "Americans with Disabilities Act" in explanation
            assert "accommodation" in explanation.lower()
            assert "reasonable" in explanation.lower()
        
        async def test_ada_undue_hardship_exception(self, system, legal_context, legal_assertions):
            """
            Test Story: Legal Researcher - Complex Legal Reasoning with Exceptions
            
            Given: ADA scenario with undue hardship defense
            When: System applies rules with exceptions
            Then: Should properly handle defeasible reasoning
            """
            # Given: ADA scenario with undue hardship
            document = RawDoc(
                id="ada-hardship-001",
                text=TestDocuments.ADA_UNDUE_HARDSHIP_SCENARIO,
                meta={"type": "employment_scenario", "domain": "ada"}
            )
            
            # When: Analyzing with undue hardship facts
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should identify both obligation and exception
            obligations = analysis_result['obligations']
            exceptions = analysis_result['exceptions']
            
            # Should have accommodation obligation
            ada_obligations = [o for o in obligations if 'accommodation' in str(o.data).lower()]
            assert len(ada_obligations) > 0
            
            # Should have undue hardship exception
            hardship_exceptions = [e for e in exceptions if 'hardship' in str(e.data).lower()]
            assert len(hardship_exceptions) > 0
            
            # Should properly resolve the conflict
            final_conclusion = analysis_result['final_conclusion']
            legal_assertions.assert_exception_properly_applied(final_conclusion, hardship_exceptions[0])

    class TestFLSAAnalysis:
        """Test FLSA overtime analysis workflow"""
        
        async def test_flsa_overtime_calculation(self, system, legal_context, legal_assertions):
            """
            Test Story: Legal Practitioner - FLSA Overtime Compliance
            
            Given: Employee work hours exceeding 40 hours per week
            When: System analyzes FLSA compliance
            Then: Should calculate proper overtime obligations
            """
            # Given: FLSA overtime scenario
            document = RawDoc(
                id="flsa-overtime-001",
                text=TestDocuments.FLSA_OVERTIME_SCENARIO,
                meta={"type": "employment_scenario", "domain": "flsa"}
            )
            
            # When: Analyzing for FLSA compliance
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should extract work hours and wage information
            entities = analysis_result['entities']
            work_hours = [e for e in entities if e.type == 'WorkHours']
            wages = [e for e in entities if e.type == 'Wage']
            
            assert len(work_hours) > 0, "Should extract work hours"
            assert len(wages) > 0, "Should extract wage information"
            
            # Should calculate proper overtime hours (54 - 40 = 14 hours)
            overtime_hours = work_hours[0].data.get('overtime_hours')
            assert overtime_hours == 14, f"Should calculate 14 overtime hours, got {overtime_hours}"
            
            # Should derive overtime payment obligation
            obligations = analysis_result['obligations']
            overtime_obligations = [o for o in obligations if 'overtime' in str(o.data).lower()]
            assert len(overtime_obligations) > 0, "Should derive overtime payment obligation"
            
            # Should specify 1.5x rate
            obligation = overtime_obligations[0]
            assert '1.5' in str(obligation.data) or 'time and a half' in str(obligation.data)
            
            # Should have FLSA authority
            legal_assertions.assert_contains_legal_authority(obligation.prov.source, "29 U.S.C.")

    class TestWorkersCompAnalysis:
        """Test Workers Compensation analysis workflow"""
        
        async def test_workers_comp_causation_chain(self, system, legal_context, legal_assertions):
            """
            Test Story: Legal Researcher - Causation Chain Analysis
            
            Given: Workplace injury scenario
            When: System analyzes causation and liability
            Then: Should establish proper causal relationships
            """
            # Given: Workers compensation scenario
            document = RawDoc(
                id="workers-comp-001",
                text=TestDocuments.WORKERS_COMP_SCENARIO,
                meta={"type": "employment_scenario", "domain": "workers_comp"}
            )
            
            # When: Analyzing causation chain
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should extract injury and workplace condition entities
            entities = analysis_result['entities']
            injuries = [e for e in entities if e.type == 'WorkplaceInjury']
            conditions = [e for e in entities if e.type == 'WorkplaceCondition']
            
            assert len(injuries) > 0, "Should extract workplace injury"
            assert len(conditions) > 0, "Should extract workplace conditions"
            
            # Should establish causation relationships
            relations = analysis_result['relations']
            causation_relations = [r for r in relations if r.relation == 'causation']
            assert len(causation_relations) > 0, "Should establish causation relationships"
            
            # Should derive compensation obligation
            obligations = analysis_result['obligations']
            comp_obligations = [o for o in obligations if 'compensation' in str(o.data).lower()]
            assert len(comp_obligations) > 0, "Should derive workers compensation obligation"

    class TestAtWillAnalysis:
        """Test At-Will Employment analysis workflow"""
        
        async def test_wrongful_termination_analysis(self, system, legal_context, legal_assertions):
            """
            Test Story: Legal Practitioner - Wrongful Termination Analysis
            
            Given: Termination scenario with protected activity
            When: System analyzes termination legality
            Then: Should identify potential wrongful termination
            """
            # Given: At-will termination with retaliation
            document = RawDoc(
                id="at-will-001",
                text=TestDocuments.AT_WILL_RETALIATION_SCENARIO,
                meta={"type": "employment_scenario", "domain": "at_will"}
            )
            
            # When: Analyzing termination legality
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should identify protected activity
            entities = analysis_result['entities']
            protected_activities = [e for e in entities if 'complaint' in str(e.data).lower()]
            assert len(protected_activities) > 0, "Should identify protected activity (complaint)"
            
            # Should identify temporal relationship
            relations = analysis_result['relations']
            temporal_relations = [r for r in relations if r.relation == 'temporal']
            assert len(temporal_relations) > 0, "Should establish temporal relationship"
            
            # Should flag potential retaliation
            violations = analysis_result['violations']
            retaliation_violations = [v for v in violations if 'retaliation' in str(v.data).lower()]
            assert len(retaliation_violations) > 0, "Should identify potential retaliation"

    class TestCrossDomainAnalysis:
        """Test analysis spanning multiple legal domains"""
        
        async def test_multi_domain_scenario(self, system, legal_context, legal_assertions):
            """
            Test Story: In-House Counsel - Complex Multi-Domain Analysis
            
            Given: Scenario involving multiple employment law domains
            When: System applies rules from different domains
            Then: Should derive obligations from all applicable domains
            """
            # Given: Complex scenario involving ADA + FLSA
            document = RawDoc(
                id="multi-domain-001", 
                text=TestDocuments.MULTI_DOMAIN_SCENARIO,
                meta={"type": "employment_scenario", "domain": "multi"}
            )
            
            # When: Analyzing multi-domain scenario
            analysis_result = await system.analyze_document(document, legal_context)
            
            # Then: Should derive obligations from multiple domains
            obligations = analysis_result['obligations']
            
            ada_obligations = [o for o in obligations if 'accommodation' in str(o.data).lower()]
            flsa_obligations = [o for o in obligations if 'overtime' in str(o.data).lower()]
            
            assert len(ada_obligations) > 0, "Should derive ADA obligations"
            assert len(flsa_obligations) > 0, "Should derive FLSA obligations"
            
            # Each obligation should have independent justification
            for obligation in ada_obligations + flsa_obligations:
                explanation = await system.explain_conclusion(obligation.id)
                assert len(explanation) > 0, f"Should explain obligation {obligation.id}"
                legal_assertions.assert_valid_explanation_chain(explanation)


class TestProvenanceTracking:
    """Test provenance tracking throughout the analysis pipeline"""
    
    @pytest.fixture
    def sample_document(self):
        return RawDoc(
            id="provenance-test",
            text="Test document for provenance tracking",
            meta={"test": True}
        )
    
    async def test_end_to_end_provenance_chain(self, system, sample_document, legal_context):
        """
        Test Story: Legal Researcher - Complete Provenance Verification
        
        Given: Any legal analysis
        When: System processes document and derives conclusions
        Then: Every conclusion should have complete provenance chain
        """
        # When: Processing document
        analysis_result = await system.analyze_document(sample_document, legal_context)
        
        # Then: Every entity should have provenance
        for entity in analysis_result['entities']:
            assert entity.prov is not None, f"Entity {entity.id} missing provenance"
            assert entity.prov.source, f"Entity {entity.id} missing source"
            assert entity.prov.method, f"Entity {entity.id} missing method"
            assert entity.prov.agent, f"Entity {entity.id} missing agent"
            assert isinstance(entity.prov.time, datetime), f"Entity {entity.id} missing timestamp"
            assert 0.0 <= entity.prov.confidence <= 1.0, f"Entity {entity.id} invalid confidence"
        
        # And: Every derived conclusion should trace back to sources
        for obligation in analysis_result.get('obligations', []):
            assert obligation.prov.derivation, f"Obligation {obligation.id} missing derivation chain"
            
            # Should trace back to original document
            derivation_chain = await system.get_derivation_chain(obligation.id)
            source_documents = [step for step in derivation_chain if step.get('type') == 'document']
            assert len(source_documents) > 0, "Should trace back to source document"
    
    async def test_provenance_composition(self, system, sample_document, legal_context):
        """
        Test Story: Legal Researcher - Provenance Composition Rules
        
        Given: Rule application combining multiple premises
        When: System derives conclusions from multiple sources
        Then: Provenance should properly compose confidence and sources
        """
        # When: Processing document with multiple entities
        analysis_result = await system.analyze_document(sample_document, legal_context)
        
        # Then: Derived facts should have composed provenance
        for obligation in analysis_result.get('obligations', []):
            # Should include sources from all premises
            all_sources = []
            if obligation.prov.derivation:
                for premise_id in obligation.prov.derivation:
                    premise = await system.get_node(premise_id)
                    if premise:
                        all_sources.extend(premise.prov.source)
            
            # Should include rule authority
            rule_sources = [s for s in obligation.prov.source if s.get('type') == 'legal_authority']
            assert len(rule_sources) > 0, "Should include legal authority source"
            
            # Confidence should be reasonable composition
            assert obligation.prov.confidence > 0.0, "Composed confidence should be positive"


class TestExplanationGeneration:
    """Test explanation generation for legal conclusions"""
    
    async def test_statutory_explanation_generation(self, system, legal_context):
        """
        Test Story: Legal Practitioner - Legal Advisory Generation
        
        Given: A derived legal obligation
        When: System generates explanation
        Then: Should provide complete statutory explanation with citations
        """
        # Given: Process ADA scenario to get obligation
        document = RawDoc(
            id="explanation-test",
            text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
            meta={"type": "employment_scenario"}
        )
        
        analysis_result = await system.analyze_document(document, legal_context)
        obligations = analysis_result['obligations']
        ada_obligations = [o for o in obligations if 'accommodation' in str(o.data).lower()]
        
        assert len(ada_obligations) > 0, "Need ADA obligation for explanation test"
        obligation = ada_obligations[0]
        
        # When: Generating explanation
        explanation = await system.explain_conclusion(obligation.id, mode='statutory')
        
        # Then: Should include statutory references
        assert "42 U.S.C." in explanation or "ADA" in explanation
        assert "accommodation" in explanation.lower()
        
        # Should include reasoning chain
        assert "because" in explanation.lower() or "due to" in explanation.lower()
        
        # Should be suitable for legal advisory
        assert len(explanation) > 100, "Explanation should be comprehensive"
    
    async def test_counterfactual_explanation(self, system, legal_context):
        """
        Test Story: Legal Researcher - Counterfactual Analysis
        
        Given: A legal conclusion
        When: System generates counterfactual explanation
        Then: Should show what would change if key facts were different
        """
        # Given: Process FLSA scenario
        document = RawDoc(
            id="counterfactual-test",
            text=TestDocuments.FLSA_OVERTIME_SCENARIO,
            meta={"type": "employment_scenario"}
        )
        
        analysis_result = await system.analyze_document(document, legal_context)
        obligations = analysis_result['obligations']
        overtime_obligations = [o for o in obligations if 'overtime' in str(o.data).lower()]
        
        assert len(overtime_obligations) > 0, "Need overtime obligation for counterfactual test"
        obligation = overtime_obligations[0]
        
        # When: Generating counterfactual explanation
        explanation = await system.explain_conclusion(obligation.id, mode='counterfactual')
        
        # Then: Should include counterfactual reasoning
        assert "if" in explanation.lower()
        assert "would not" in explanation.lower() or "wouldn't" in explanation.lower()
        
        # Should mention key conditions
        assert "40 hours" in explanation or "overtime" in explanation.lower()


class TestSystemIntegration:
    """Test integration aspects and workflow orchestration"""
    
    async def test_plugin_system_integration(self, system):
        """
        Test Story: System Administrator - Plugin Management
        
        Given: Legal hypergraph system
        When: Loading and managing plugins
        Then: Should properly integrate plugin capabilities
        """
        # Then: Should have employment plugin loaded
        plugins = await system.list_plugins()
        assert 'employment-us' in plugins, "Employment plugin should be loaded"
        
        # Should provide all required capabilities
        plugin = await system.get_plugin('employment-us')
        assert plugin.provides_ontology, "Should provide ontology"
        assert plugin.provides_mapping, "Should provide mapping"
        assert plugin.provides_rules, "Should provide rules"
        assert plugin.provides_explanation, "Should provide explanation"
    
    async def test_concurrent_analysis_handling(self, system, legal_context):
        """
        Test Story: Legal Operations Director - High-Volume Processing
        
        Given: Multiple documents for analysis
        When: Processing documents concurrently
        Then: Should handle concurrent analysis without conflicts
        """
        # Given: Multiple test documents
        documents = [
            RawDoc(id=f"concurrent-{i}", text=TestDocuments.ADA_ACCOMMODATION_REQUEST, meta={})
            for i in range(5)
        ]
        
        # When: Processing concurrently
        tasks = [system.analyze_document(doc, legal_context) for doc in documents]
        results = await asyncio.gather(*tasks)
        
        # Then: All should complete successfully
        assert len(results) == 5, "All analyses should complete"
        
        for result in results:
            assert 'entities' in result, "Each result should have entities"
            assert len(result['entities']) > 0, "Each result should extract entities"
    
    async def test_performance_requirements(self, system, legal_context):
        """
        Test Story: Performance Engineer - Response Time Requirements
        
        Given: Legal document under 10,000 words
        When: Analyzing document
        Then: Should complete within 2 minutes
        """
        import time
        
        # Given: Standard test document
        document = RawDoc(
            id="performance-test",
            text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
            meta={"performance_test": True}
        )
        
        # When: Timing analysis
        start_time = time.time()
        analysis_result = await system.analyze_document(document, legal_context)
        end_time = time.time()
        
        # Then: Should complete within 2 minutes (120 seconds)
        analysis_time = end_time - start_time
        assert analysis_time < 120, f"Analysis took {analysis_time}s, should be under 120s"
        
        # And: Should still produce quality results
        assert len(analysis_result['entities']) > 0, "Should extract entities despite time constraint"


# Utility functions for test setup and validation
async def setup_test_data():
    """Set up common test data and fixtures"""
    pass

async def cleanup_test_data():
    """Clean up test data after tests"""
    pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])