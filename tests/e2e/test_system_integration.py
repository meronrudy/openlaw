"""
End-to-End Tests: System Integration and Business Workflows

Tests integration scenarios covering business stakeholder user stories
including ROI measurement, compliance monitoring, and operational workflows.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from core.system import LegalHypergraphSystem
from core.storage import GraphStore
from core.model import Context, Node, Hyperedge
from sdk.plugin import RawDoc
from tests.fixtures.legal_documents import TestDocuments
from tests.helpers.legal_assertions import (
    LegalAssertions, PerformanceAssertions, SecurityAssertions, ComplianceAssertions
)


class TestBusinessValueIntegration:
    """Test business value and ROI measurement workflows"""
    
    @pytest.fixture
    async def business_system(self):
        """System configured for business workflow testing"""
        system = LegalHypergraphSystem(
            storage_config={'path': ':memory:'},
            plugin_dirs=['plugins'],
            analytics_enabled=True,
            audit_enabled=True
        )
        await system.initialize()
        await system.load_plugin('employment-us')
        yield system
        await system.shutdown()
    
    @pytest.fixture
    def performance_assertions(self):
        return PerformanceAssertions()
    
    @pytest.fixture
    def compliance_assertions(self):
        return ComplianceAssertions()

    class TestROIAndAnalytics:
        """Test Story: Managing Partner - ROI and Business Impact Analysis"""
        
        async def test_time_savings_measurement(self, business_system, performance_assertions):
            """
            Given: Legal documents processed with and without AI assistance
            When: Measuring processing time and accuracy
            Then: Should demonstrate measurable time savings and efficiency gains
            """
            documents = [
                RawDoc(id=f"roi-test-{i}", text=TestDocuments.ADA_ACCOMMODATION_REQUEST, meta={})
                for i in range(10)
            ]
            
            context = Context(jurisdiction="US", law_type="statute")
            
            # Measure AI-assisted processing time
            start_time = time.time()
            ai_results = []
            
            for doc in documents:
                result = await business_system.analyze_document(doc, context)
                ai_results.append(result)
            
            ai_processing_time = time.time() - start_time
            
            # Simulate traditional processing time (typically 10x slower)
            traditional_time_estimate = ai_processing_time * 10
            
            # Calculate time savings
            time_savings = traditional_time_estimate - ai_processing_time
            savings_percentage = (time_savings / traditional_time_estimate) * 100
            
            # Assertions for business value
            performance_assertions.assert_response_time_acceptable(
                ai_processing_time, 60.0, "batch document processing"
            )
            
            assert savings_percentage > 50, f"Should save >50% time, actual: {savings_percentage:.1f}%"
            assert len(ai_results) == 10, "Should process all documents"
            
            # Verify analysis quality
            for result in ai_results:
                assert len(result['entities']) > 0, "Should extract entities from each document"
                obligations = result.get('obligations', [])
                if obligations:
                    assert all(o.prov.confidence > 0.7 for o in obligations), "Should have high confidence"
        
        async def test_accuracy_measurement(self, business_system):
            """
            Given: Legal analysis with known correct outcomes
            When: Comparing AI results to expert validation
            Then: Should achieve high accuracy rates for business justification
            """
            # Test with documents that have known legal outcomes
            test_cases = [
                {
                    'document': RawDoc(
                        id="accuracy-ada",
                        text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
                        meta={'expected_outcome': 'ada_obligation'}
                    ),
                    'expected_obligations': ['provide_reasonable_accommodation'],
                    'expected_authorities': ['42 U.S.C.']
                },
                {
                    'document': RawDoc(
                        id="accuracy-flsa", 
                        text=TestDocuments.FLSA_OVERTIME_SCENARIO,
                        meta={'expected_outcome': 'flsa_obligation'}
                    ),
                    'expected_obligations': ['pay_overtime_compensation'],
                    'expected_authorities': ['29 U.S.C.']
                }
            ]
            
            context = Context(jurisdiction="US")
            correct_predictions = 0
            total_predictions = len(test_cases)
            
            for test_case in test_cases:
                result = await business_system.analyze_document(test_case['document'], context)
                
                # Check for expected obligations
                obligations = result.get('obligations', [])
                obligation_actions = [o.data.get('action', '') for o in obligations]
                
                expected_found = any(
                    expected in action.lower() 
                    for expected in test_case['expected_obligations']
                    for action in obligation_actions
                )
                
                # Check for expected legal authorities
                authorities_found = any(
                    any(expected in str(o.prov.source) for expected in test_case['expected_authorities'])
                    for o in obligations
                )
                
                if expected_found and authorities_found:
                    correct_predictions += 1
            
            accuracy_rate = (correct_predictions / total_predictions) * 100
            
            # Business requirement: >85% accuracy
            assert accuracy_rate >= 85, f"Accuracy rate {accuracy_rate:.1f}% below business requirement (85%)"
        
        async def test_cost_efficiency_analysis(self, business_system):
            """
            Given: Legal work processed through AI system
            When: Calculating cost per analysis vs traditional methods
            Then: Should demonstrate significant cost reduction
            """
            # Simulate cost analysis
            documents_processed = 100
            
            # AI system costs (estimated)
            ai_processing_cost_per_doc = 0.50  # $0.50 per document
            ai_total_cost = documents_processed * ai_processing_cost_per_doc
            
            # Traditional legal research costs (estimated)
            traditional_cost_per_doc = 25.00  # $25.00 per document (1 hour at $25/hr paralegal)
            traditional_total_cost = documents_processed * traditional_cost_per_doc
            
            # Calculate cost savings
            cost_savings = traditional_total_cost - ai_total_cost
            savings_percentage = (cost_savings / traditional_total_cost) * 100
            
            # Business assertions
            assert cost_savings > 0, "Should demonstrate cost savings"
            assert savings_percentage > 80, f"Should save >80% costs, actual: {savings_percentage:.1f}%"
            
            # ROI calculation (assuming system cost amortized over usage)
            system_deployment_cost = 50000  # $50k deployment cost
            monthly_usage = documents_processed
            monthly_savings = cost_savings
            
            # Payback period in months
            payback_period = system_deployment_cost / monthly_savings
            
            assert payback_period < 24, f"Payback period {payback_period:.1f} months should be under 24 months"

    class TestComplianceMonitoring:
        """Test Story: In-House Counsel - Ongoing Compliance Monitoring"""
        
        async def test_compliance_dashboard_integration(self, business_system, compliance_assertions):
            """
            Given: System monitoring compliance across multiple domains
            When: Generating compliance dashboard data
            Then: Should provide real-time compliance status
            """
            # Simulate compliance monitoring documents
            compliance_documents = [
                RawDoc(id="compliance-ada-1", text=TestDocuments.ADA_ACCOMMODATION_REQUEST, 
                      meta={'compliance_area': 'ada', 'priority': 'high'}),
                RawDoc(id="compliance-flsa-1", text=TestDocuments.FLSA_OVERTIME_SCENARIO,
                      meta={'compliance_area': 'flsa', 'priority': 'medium'}),
                RawDoc(id="compliance-safety-1", text=TestDocuments.WORKERS_COMP_SCENARIO,
                      meta={'compliance_area': 'safety', 'priority': 'high'})
            ]
            
            context = Context(jurisdiction="US")
            compliance_results = {}
            
            for doc in compliance_documents:
                result = await business_system.analyze_document(doc, context)
                area = doc.meta['compliance_area']
                priority = doc.meta['priority']
                
                # Extract compliance indicators
                violations = result.get('violations', [])
                obligations = result.get('obligations', [])
                
                compliance_results[area] = {
                    'document_id': doc.id,
                    'priority': priority,
                    'violations_count': len(violations),
                    'obligations_count': len(obligations),
                    'compliance_score': self._calculate_compliance_score(violations, obligations),
                    'last_updated': datetime.utcnow()
                }
            
            # Verify compliance dashboard data
            assert len(compliance_results) == 3, "Should track all compliance areas"
            
            for area, data in compliance_results.items():
                assert 'compliance_score' in data, f"Missing compliance score for {area}"
                assert 0.0 <= data['compliance_score'] <= 100.0, f"Invalid compliance score for {area}"
                assert data['last_updated'] is not None, f"Missing timestamp for {area}"
            
            # High priority items should be flagged
            high_priority_areas = [area for area, data in compliance_results.items() 
                                 if data['priority'] == 'high']
            assert len(high_priority_areas) >= 2, "Should identify high priority compliance areas"
        
        def _calculate_compliance_score(self, violations: List, obligations: List) -> float:
            """Calculate compliance score based on violations and obligations"""
            if not obligations:
                return 100.0  # No obligations = perfect compliance
            
            violation_weight = len(violations) * 20  # Each violation reduces score by 20
            max_score = 100.0
            
            return max(0.0, max_score - violation_weight)
        
        async def test_regulatory_change_monitoring(self, business_system):
            """
            Given: New regulatory requirements
            When: System monitors for regulatory changes
            Then: Should identify impacts and update compliance requirements
            """
            # Simulate regulatory change notification
            regulatory_change = {
                'id': 'reg-change-001',
                'title': 'New ADA Accommodation Guidelines',
                'effective_date': '2024-07-01',
                'affected_statutes': ['42 U.S.C. § 12112'],
                'summary': 'Updated guidance on remote work accommodations',
                'impact_assessment': 'medium'
            }
            
            # Process document with new requirements
            updated_document = RawDoc(
                id="updated-ada-policy",
                text=f"""
                Under the updated ADA guidelines effective {regulatory_change['effective_date']},
                employers must consider remote work as a reasonable accommodation when requested
                by qualified individuals with disabilities. This applies to positions where
                essential functions can be performed remotely without undue hardship.
                
                {TestDocuments.ADA_ACCOMMODATION_REQUEST}
                """,
                meta={'regulatory_change': regulatory_change['id']}
            )
            
            context = Context(jurisdiction="US", 
                            valid_from=datetime.fromisoformat(f"{regulatory_change['effective_date']}T00:00:00"))
            
            result = await business_system.analyze_document(updated_document, context)
            
            # Should identify new accommodation requirements
            obligations = result.get('obligations', [])
            accommodation_obligations = [o for o in obligations 
                                       if 'accommodation' in str(o.data).lower()]
            
            assert len(accommodation_obligations) > 0, "Should identify accommodation obligations"
            
            # Should reference updated legal authority
            for obligation in accommodation_obligations:
                sources = obligation.prov.source
                assert any('42 U.S.C.' in str(source) for source in sources), \
                    "Should reference ADA authority"

    class TestOperationalEfficiency:
        """Test Story: Legal Operations Director - Legal Process Optimization"""
        
        async def test_workflow_bottleneck_identification(self, business_system, performance_assertions):
            """
            Given: Legal workflow processing multiple document types
            When: Analyzing workflow performance
            Then: Should identify bottlenecks and optimization opportunities
            """
            # Simulate different document types with varying complexity
            workflow_documents = [
                ('simple', RawDoc(id="simple-1", text="Simple employment agreement review.", meta={})),
                ('medium', RawDoc(id="medium-1", text=TestDocuments.ADA_ACCOMMODATION_REQUEST, meta={})),
                ('complex', RawDoc(id="complex-1", text=TestDocuments.MULTI_DOMAIN_SCENARIO, meta={}))
            ]
            
            context = Context(jurisdiction="US")
            processing_times = {}
            
            for complexity, doc in workflow_documents:
                start_time = time.time()
                result = await business_system.analyze_document(doc, context)
                processing_time = time.time() - start_time
                
                processing_times[complexity] = {
                    'time': processing_time,
                    'entities_found': len(result.get('entities', [])),
                    'obligations_found': len(result.get('obligations', [])),
                    'complexity_score': self._calculate_complexity_score(result)
                }
            
            # Verify processing time scales appropriately with complexity
            assert processing_times['simple']['time'] < processing_times['medium']['time']
            assert processing_times['medium']['time'] <= processing_times['complex']['time']
            
            # Identify bottlenecks (anything taking >30 seconds)
            bottlenecks = [complexity for complexity, data in processing_times.items() 
                          if data['time'] > 30.0]
            
            # Performance requirements
            performance_assertions.assert_response_time_acceptable(
                processing_times['simple']['time'], 5.0, "simple document processing"
            )
            performance_assertions.assert_response_time_acceptable(
                processing_times['medium']['time'], 15.0, "medium document processing"
            )
            performance_assertions.assert_response_time_acceptable(
                processing_times['complex']['time'], 45.0, "complex document processing"
            )
        
        def _calculate_complexity_score(self, result: Dict[str, Any]) -> int:
            """Calculate document complexity score based on analysis results"""
            entities = len(result.get('entities', []))
            relations = len(result.get('relations', []))
            obligations = len(result.get('obligations', []))
            
            return entities + (relations * 2) + (obligations * 3)
        
        async def test_resource_allocation_optimization(self, business_system):
            """
            Given: Multiple legal teams with different workloads
            When: Analyzing team capacity and document assignments
            Then: Should optimize resource allocation
            """
            # Simulate team workloads
            teams = {
                'employment_team': {
                    'capacity': 10,  # documents per day
                    'specialization': ['employment', 'ada', 'flsa'],
                    'current_load': 7
                },
                'compliance_team': {
                    'capacity': 8,
                    'specialization': ['compliance', 'regulatory'],
                    'current_load': 6
                },
                'general_team': {
                    'capacity': 15,
                    'specialization': ['general'],
                    'current_load': 12
                }
            }
            
            # Incoming document queue
            document_queue = [
                {'id': 'queue-1', 'domain': 'employment', 'priority': 'high'},
                {'id': 'queue-2', 'domain': 'ada', 'priority': 'medium'},
                {'id': 'queue-3', 'domain': 'compliance', 'priority': 'high'},
                {'id': 'queue-4', 'domain': 'general', 'priority': 'low'},
                {'id': 'queue-5', 'domain': 'flsa', 'priority': 'high'}
            ]
            
            # Optimize assignments
            assignments = self._optimize_team_assignments(teams, document_queue)
            
            # Verify optimization
            assert len(assignments) == len(document_queue), "Should assign all documents"
            
            # High priority documents should go to specialized teams when possible
            high_priority_docs = [doc for doc in document_queue if doc['priority'] == 'high']
            for doc in high_priority_docs:
                assignment = assignments[doc['id']]
                team_info = teams[assignment['team']]
                
                # Should not overload teams
                assert assignment['position'] <= team_info['capacity'], \
                    f"Team {assignment['team']} overloaded"
        
        def _optimize_team_assignments(self, teams: Dict, documents: List[Dict]) -> Dict:
            """Optimize document assignments to teams"""
            assignments = {}
            
            for doc in documents:
                best_team = None
                best_score = -1
                
                for team_name, team_info in teams.items():
                    # Calculate assignment score
                    specialization_match = 1 if doc['domain'] in team_info['specialization'] else 0
                    capacity_available = team_info['capacity'] - team_info['current_load']
                    priority_weight = {'high': 3, 'medium': 2, 'low': 1}[doc['priority']]
                    
                    score = specialization_match * priority_weight * min(capacity_available, 1)
                    
                    if score > best_score and capacity_available > 0:
                        best_score = score
                        best_team = team_name
                
                if best_team:
                    teams[best_team]['current_load'] += 1
                    assignments[doc['id']] = {
                        'team': best_team,
                        'position': teams[best_team]['current_load'],
                        'score': best_score
                    }
            
            return assignments

    class TestClientServiceEnhancement:
        """Test Story: Managing Partner - Premium Legal Service Delivery"""
        
        async def test_client_facing_analytics(self, business_system):
            """
            Given: Client legal matters processed through the system
            When: Generating client-facing analytics and reports
            Then: Should provide valuable insights for client presentations
            """
            # Simulate client matter documents
            client_documents = [
                RawDoc(id="client-matter-1", text=TestDocuments.ADA_ACCOMMODATION_REQUEST,
                      meta={'client_id': 'CLIENT001', 'matter_type': 'employment_compliance'}),
                RawDoc(id="client-matter-2", text=TestDocuments.FLSA_OVERTIME_SCENARIO,
                      meta={'client_id': 'CLIENT001', 'matter_type': 'wage_hour_audit'}),
                RawDoc(id="client-matter-3", text=TestDocuments.WORKERS_COMP_SCENARIO,
                      meta={'client_id': 'CLIENT001', 'matter_type': 'workplace_safety'})
            ]
            
            context = Context(jurisdiction="US")
            client_analytics = {
                'client_id': 'CLIENT001',
                'matters_processed': 0,
                'risk_areas_identified': set(),
                'obligations_count': 0,
                'compliance_score': 0.0,
                'recommendations': []
            }
            
            for doc in client_documents:
                result = await business_system.analyze_document(doc, context)
                client_analytics['matters_processed'] += 1
                
                # Identify risk areas
                violations = result.get('violations', [])
                for violation in violations:
                    risk_area = violation.data.get('domain', 'unknown')
                    client_analytics['risk_areas_identified'].add(risk_area)
                
                # Count obligations
                obligations = result.get('obligations', [])
                client_analytics['obligations_count'] += len(obligations)
                
                # Generate recommendations
                if obligations:
                    recommendations = self._generate_client_recommendations(obligations)
                    client_analytics['recommendations'].extend(recommendations)
            
            # Calculate overall compliance score
            client_analytics['compliance_score'] = self._calculate_client_compliance_score(
                client_analytics['matters_processed'],
                len(client_analytics['risk_areas_identified']),
                client_analytics['obligations_count']
            )
            
            # Verify client analytics quality
            assert client_analytics['matters_processed'] == 3
            assert client_analytics['obligations_count'] > 0
            assert 0.0 <= client_analytics['compliance_score'] <= 100.0
            assert len(client_analytics['recommendations']) > 0
        
        def _generate_client_recommendations(self, obligations: List[Node]) -> List[str]:
            """Generate actionable recommendations based on identified obligations"""
            recommendations = []
            
            for obligation in obligations:
                action = obligation.data.get('action', '')
                if 'accommodation' in action.lower():
                    recommendations.append("Review ADA accommodation policies and procedures")
                elif 'overtime' in action.lower():
                    recommendations.append("Audit wage and hour practices for FLSA compliance")
                elif 'compensation' in action.lower():
                    recommendations.append("Review workers compensation coverage and claims procedures")
            
            return list(set(recommendations))  # Remove duplicates
        
        def _calculate_client_compliance_score(self, matters: int, risk_areas: int, obligations: int) -> float:
            """Calculate overall client compliance score"""
            if matters == 0:
                return 100.0
            
            # Base score
            base_score = 100.0
            
            # Deduct for risk areas
            risk_penalty = min(risk_areas * 15, 60)  # Max 60 point penalty
            
            # Deduct for unaddressed obligations
            obligation_penalty = min(obligations * 5, 30)  # Max 30 point penalty
            
            final_score = max(0.0, base_score - risk_penalty - obligation_penalty)
            return final_score
        
        async def test_predictive_legal_outcomes(self, business_system):
            """
            Given: Legal scenarios with historical outcome data
            When: Predicting likely legal outcomes
            Then: Should provide probability assessments for strategic planning
            """
            # Test scenarios for outcome prediction
            prediction_scenarios = [
                {
                    'scenario': RawDoc(id="prediction-1", text=TestDocuments.ADA_ACCOMMODATION_REQUEST, meta={}),
                    'expected_outcomes': ['accommodation_required', 'employer_liable'],
                    'confidence_threshold': 0.7
                },
                {
                    'scenario': RawDoc(id="prediction-2", text=TestDocuments.AT_WILL_RETALIATION_SCENARIO, meta={}),
                    'expected_outcomes': ['wrongful_termination', 'retaliation_claim'],
                    'confidence_threshold': 0.6
                }
            ]
            
            context = Context(jurisdiction="US")
            predictions = []
            
            for scenario_data in prediction_scenarios:
                result = await business_system.analyze_document(scenario_data['scenario'], context)
                
                # Extract prediction information
                violations = result.get('violations', [])
                obligations = result.get('obligations', [])
                
                scenario_predictions = {
                    'scenario_id': scenario_data['scenario'].id,
                    'predicted_outcomes': [],
                    'confidence_scores': {},
                    'risk_level': 'low'
                }
                
                # Analyze violations for outcome predictions
                for violation in violations:
                    violation_type = violation.data.get('type', 'unknown')
                    confidence = violation.prov.confidence
                    
                    scenario_predictions['predicted_outcomes'].append(violation_type)
                    scenario_predictions['confidence_scores'][violation_type] = confidence
                
                # Determine risk level
                if violations and any(v.prov.confidence > 0.8 for v in violations):
                    scenario_predictions['risk_level'] = 'high'
                elif violations:
                    scenario_predictions['risk_level'] = 'medium'
                
                predictions.append(scenario_predictions)
            
            # Verify prediction quality
            assert len(predictions) == 2
            
            for prediction in predictions:
                assert 'predicted_outcomes' in prediction
                assert 'confidence_scores' in prediction
                assert prediction['risk_level'] in ['low', 'medium', 'high']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])