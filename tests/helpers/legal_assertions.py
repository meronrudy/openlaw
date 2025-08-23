"""
Legal-Specific Test Assertions

Custom assertion helpers for validating legal reasoning, provenance,
and compliance with legal requirements in test scenarios.
"""

from typing import List, Dict, Any, Set
from datetime import datetime
import re

from core.model import Node, Hyperedge, Provenance, Context


class LegalAssertions:
    """Custom assertions for legal hypergraph testing"""
    
    def assert_contains_entity_types(self, actual_types: Set[str], expected_types: List[str], 
                                   message: str = None):
        """Assert that all expected entity types are present"""
        missing_types = set(expected_types) - actual_types
        if missing_types:
            msg = message or f"Missing entity types: {missing_types}. Found: {actual_types}"
            raise AssertionError(msg)
    
    def assert_valid_provenance(self, prov: Provenance, message: str = None):
        """Assert that provenance meets legal requirements"""
        errors = []
        
        if not prov.source:
            errors.append("Missing source information")
        
        if not prov.method:
            errors.append("Missing method information")
            
        if not prov.agent:
            errors.append("Missing agent information")
            
        if not isinstance(prov.time, datetime):
            errors.append("Missing or invalid timestamp")
            
        if not (0.0 <= prov.confidence <= 1.0):
            errors.append(f"Invalid confidence score: {prov.confidence}")
            
        # Check source completeness
        for source in prov.source:
            if not isinstance(source, dict):
                errors.append("Source must be a dictionary")
                continue
                
            if 'type' not in source:
                errors.append("Source missing type field")
                
            if source.get('type') in ['document', 'case', 'statute'] and 'id' not in source:
                errors.append("Source missing identifier")
        
        if errors:
            msg = message or f"Invalid provenance: {'; '.join(errors)}"
            raise AssertionError(msg)
    
    def assert_contains_legal_authority(self, sources: List[Dict[str, Any]], 
                                      authority_pattern: str, message: str = None):
        """Assert that provenance contains specific legal authority"""
        authority_found = False
        
        for source in sources:
            if 'cite' in source and authority_pattern in source['cite']:
                authority_found = True
                break
            if 'id' in source and authority_pattern in source['id']:
                authority_found = True
                break
                
        if not authority_found:
            msg = message or f"Legal authority '{authority_pattern}' not found in sources: {sources}"
            raise AssertionError(msg)
    
    def assert_proper_citation_format(self, citation: str, citation_type: str = None, 
                                    message: str = None):
        """Assert that legal citations follow proper format"""
        if citation_type == 'statute':
            # Check for USC pattern: "XX U.S.C. § XXXX"
            usc_pattern = r'\d+\s+U\.S\.C\.?\s*§?\s*\d+'
            if not re.search(usc_pattern, citation, re.IGNORECASE):
                msg = message or f"Invalid USC citation format: {citation}"
                raise AssertionError(msg)
                
        elif citation_type == 'case':
            # Check for case pattern: "Name v. Name, XXX F.Xd XXX"
            case_pattern = r'\w+\s+v\.?\s+\w+.*\d+.*\d+'
            if not re.search(case_pattern, citation, re.IGNORECASE):
                msg = message or f"Invalid case citation format: {citation}"
                raise AssertionError(msg)
    
    def assert_reasoning_chain_complete(self, conclusion_id: str, 
                                      derivation_chain: List[Dict[str, Any]], 
                                      message: str = None):
        """Assert that reasoning chain is complete and traceable"""
        if not derivation_chain:
            msg = message or f"Empty derivation chain for conclusion {conclusion_id}"
            raise AssertionError(msg)
            
        # Check that chain includes original source
        has_source = any(step.get('type') == 'document' for step in derivation_chain)
        if not has_source:
            msg = message or f"Derivation chain missing source document for {conclusion_id}"
            raise AssertionError(msg)
            
        # Check that chain includes legal rule
        has_rule = any(step.get('type') == 'rule' for step in derivation_chain)
        if not has_rule:
            msg = message or f"Derivation chain missing legal rule for {conclusion_id}"
            raise AssertionError(msg)
    
    def assert_obligation_structure_valid(self, obligation: Node, message: str = None):
        """Assert that legal obligation has required structure"""
        errors = []
        
        if obligation.type != 'Obligation':
            errors.append(f"Expected type 'Obligation', got '{obligation.type}'")
            
        required_fields = ['bearer', 'action']
        for field in required_fields:
            if field not in obligation.data:
                errors.append(f"Missing required field: {field}")
                
        # Validate bearer is an entity
        bearer = obligation.data.get('bearer')
        if bearer and not isinstance(bearer, str):
            errors.append("Bearer must be a string identifier")
            
        # Validate action is meaningful
        action = obligation.data.get('action')
        if action and len(action.strip()) < 3:
            errors.append("Action must be a meaningful description")
            
        if errors:
            msg = message or f"Invalid obligation structure: {'; '.join(errors)}"
            raise AssertionError(msg)
    
    def assert_exception_properly_applied(self, conclusion: Dict[str, Any], 
                                        exception: Node, message: str = None):
        """Assert that legal exception was properly applied"""
        # Check that conclusion reflects the exception
        if 'overridden_by' not in conclusion:
            msg = message or f"Conclusion should be marked as overridden by exception {exception.id}"
            raise AssertionError(msg)
            
        if conclusion['overridden_by'] != exception.id:
            msg = message or f"Conclusion overridden by wrong exception: expected {exception.id}, got {conclusion['overridden_by']}"
            raise AssertionError(msg)
    
    def assert_valid_explanation_chain(self, explanation: str, message: str = None):
        """Assert that explanation contains required legal reasoning elements"""
        errors = []
        
        if not explanation or len(explanation.strip()) < 50:
            errors.append("Explanation too short or empty")
            
        # Should contain legal reasoning words
        reasoning_words = ['because', 'therefore', 'since', 'under', 'pursuant to']
        if not any(word in explanation.lower() for word in reasoning_words):
            errors.append("Explanation lacks legal reasoning indicators")
            
        # Should contain legal citation patterns
        citation_patterns = [r'\d+\s+U\.S\.C\.', r'§\s*\d+', r'\w+\s+v\.?\s+\w+']
        if not any(re.search(pattern, explanation, re.IGNORECASE) for pattern in citation_patterns):
            errors.append("Explanation lacks legal citations")
            
        if errors:
            msg = message or f"Invalid explanation: {'; '.join(errors)}"
            raise AssertionError(msg)
    
    def assert_jurisdiction_consistency(self, nodes: List[Node], 
                                      expected_jurisdiction: str, message: str = None):
        """Assert that all nodes are consistent with expected jurisdiction"""
        inconsistent_nodes = []
        
        for node in nodes:
            if node.context and node.context.jurisdiction:
                if not node.context.jurisdiction.startswith(expected_jurisdiction):
                    inconsistent_nodes.append(node.id)
                    
        if inconsistent_nodes:
            msg = message or f"Nodes with inconsistent jurisdiction: {inconsistent_nodes}"
            raise AssertionError(msg)
    
    def assert_temporal_consistency(self, relations: List[Hyperedge], message: str = None):
        """Assert that temporal relationships are logically consistent"""
        temporal_relations = [r for r in relations if r.relation == 'temporal']
        
        # Check for temporal contradictions
        # This is a simplified check - real implementation would be more sophisticated
        for relation in temporal_relations:
            if 'before' in relation.qualifiers and 'after' in relation.qualifiers:
                msg = message or f"Temporal contradiction in relation {relation.id}"
                raise AssertionError(msg)
    
    def assert_confidence_reasonable(self, entities: List[Node], 
                                   min_confidence: float = 0.5, message: str = None):
        """Assert that entity extraction confidence is reasonable"""
        low_confidence_entities = []
        
        for entity in entities:
            if entity.prov.confidence < min_confidence:
                low_confidence_entities.append((entity.id, entity.prov.confidence))
                
        if low_confidence_entities:
            msg = message or f"Entities with low confidence: {low_confidence_entities}"
            raise AssertionError(msg)
    
    def assert_rule_coverage(self, applied_rules: List[str], 
                           expected_domains: List[str], message: str = None):
        """Assert that rules from expected legal domains were applied"""
        domain_coverage = {}
        
        for rule_id in applied_rules:
            # Extract domain from rule ID (convention: domain_rule_name)
            if '_' in rule_id:
                domain = rule_id.split('_')[0]
                domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
                
        missing_domains = set(expected_domains) - set(domain_coverage.keys())
        if missing_domains:
            msg = message or f"Missing coverage for domains: {missing_domains}"
            raise AssertionError(msg)
    
    def assert_no_circular_reasoning(self, derivation_chains: Dict[str, List[str]], 
                                   message: str = None):
        """Assert that there are no circular dependencies in reasoning"""
        for conclusion_id, chain in derivation_chains.items():
            if conclusion_id in chain:
                msg = message or f"Circular reasoning detected for conclusion {conclusion_id}"
                raise AssertionError(msg)
                
            # Check for indirect cycles
            visited = set()
            current = conclusion_id
            
            while current in chain and current not in visited:
                visited.add(current)
                # Get next in chain (simplified)
                current = chain[0] if chain else None
                
            if current in visited:
                msg = message or f"Indirect circular reasoning detected involving {conclusion_id}"
                raise AssertionError(msg)


class PerformanceAssertions:
    """Performance-specific assertions for legal system testing"""
    
    @staticmethod
    def assert_response_time_acceptable(actual_time: float, max_time: float, 
                                      operation: str = "operation", message: str = None):
        """Assert that operation completed within acceptable time"""
        if actual_time > max_time:
            msg = message or f"{operation} took {actual_time:.2f}s, max allowed: {max_time}s"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_memory_usage_reasonable(memory_used: int, max_memory: int, 
                                     message: str = None):
        """Assert that memory usage is within reasonable bounds"""
        if memory_used > max_memory:
            msg = message or f"Memory usage {memory_used} bytes exceeds limit {max_memory} bytes"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_concurrent_handling(concurrent_results: List[Any], 
                                 expected_count: int, message: str = None):
        """Assert that concurrent operations completed successfully"""
        successful_results = [r for r in concurrent_results if r is not None]
        
        if len(successful_results) != expected_count:
            msg = message or f"Only {len(successful_results)}/{expected_count} concurrent operations succeeded"
            raise AssertionError(msg)


class SecurityAssertions:
    """Security-specific assertions for legal system testing"""
    
    @staticmethod
    def assert_sensitive_data_protected(response: Dict[str, Any], 
                                      sensitive_patterns: List[str], 
                                      message: str = None):
        """Assert that sensitive data is not exposed in responses"""
        response_str = str(response).lower()
        
        exposed_patterns = []
        for pattern in sensitive_patterns:
            if pattern.lower() in response_str:
                exposed_patterns.append(pattern)
                
        if exposed_patterns:
            msg = message or f"Sensitive data exposed: {exposed_patterns}"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_access_control_enforced(access_result: Dict[str, Any], 
                                     expected_access: bool, message: str = None):
        """Assert that access control is properly enforced"""
        actual_access = access_result.get('access_granted', False)
        
        if actual_access != expected_access:
            msg = message or f"Access control violation: expected {expected_access}, got {actual_access}"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_audit_trail_complete(audit_log: List[Dict[str, Any]], 
                                  required_fields: List[str], message: str = None):
        """Assert that audit trail contains required information"""
        for entry in audit_log:
            missing_fields = [field for field in required_fields if field not in entry]
            if missing_fields:
                msg = message or f"Audit entry missing fields: {missing_fields}"
                raise AssertionError(msg)


class ComplianceAssertions:
    """Compliance-specific assertions for legal system testing"""
    
    @staticmethod
    def assert_gdpr_compliance(data_processing: Dict[str, Any], message: str = None):
        """Assert that data processing complies with GDPR requirements"""
        required_fields = ['purpose', 'legal_basis', 'retention_period']
        
        missing_fields = [field for field in required_fields if field not in data_processing]
        if missing_fields:
            msg = message or f"GDPR compliance violation: missing {missing_fields}"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_attorney_client_privilege_maintained(access_log: List[Dict[str, Any]], 
                                                   privileged_docs: List[str], 
                                                   message: str = None):
        """Assert that attorney-client privilege is maintained"""
        unauthorized_access = []
        
        for log_entry in access_log:
            doc_id = log_entry.get('document_id')
            user_role = log_entry.get('user_role')
            
            if doc_id in privileged_docs and user_role not in ['attorney', 'client']:
                unauthorized_access.append((doc_id, user_role))
                
        if unauthorized_access:
            msg = message or f"Privilege violations: {unauthorized_access}"
            raise AssertionError(msg)
    
    @staticmethod
    def assert_retention_policy_enforced(documents: List[Dict[str, Any]], 
                                       retention_rules: Dict[str, int], 
                                       message: str = None):
        """Assert that document retention policies are enforced"""
        violations = []
        current_time = datetime.utcnow()
        
        for doc in documents:
            doc_type = doc.get('type')
            created_time = doc.get('created_time')
            
            if doc_type in retention_rules and created_time:
                retention_days = retention_rules[doc_type]
                days_old = (current_time - created_time).days
                
                if days_old > retention_days:
                    violations.append((doc.get('id'), days_old, retention_days))
                    
        if violations:
            msg = message or f"Retention policy violations: {violations}"
            raise AssertionError(msg)