# CAP Caselaw Plugin - Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the CAP caselaw plugin, designed to ensure quality, performance, and reliability at the scale of 37M+ documents.

## 🧪 Test Pyramid Structure

### Test Levels Overview

```mermaid
graph TB
    subgraph "Test Pyramid"
        E2E[End-to-End Tests<br/>~10 tests<br/>Full System Integration]
        INT[Integration Tests<br/>~100 tests<br/>Plugin & Component Integration]  
        UNIT[Unit Tests<br/>~1000 tests<br/>Individual Components]
        PROP[Property Tests<br/>~50 tests<br/>Legal Reasoning Invariants]
    end
    
    subgraph "Specialized Testing"
        PERF[Performance Tests<br/>Load & Stress Testing]
        QUAL[Data Quality Tests<br/>Accuracy Validation]
        SEC[Security Tests<br/>Vulnerability Assessment]
    end
    
    UNIT --> INT
    INT --> E2E
    PROP --> UNIT
    PERF --> E2E
    QUAL --> INT
    SEC --> INT
```

## 🔬 Unit Testing

### Citation Extraction Tests

```python
# tests/unit/test_citation_extraction.py
import pytest
from plugins.caselaw.extraction.citation_extractor import CitationExtractor

class TestCitationExtraction:
    """Unit tests for citation extraction accuracy and performance"""
    
    def setup_method(self):
        self.extractor = CitationExtractor(self._get_test_config())
        self.test_cases = self._load_annotated_test_cases()
    
    @pytest.mark.parametrize("citation_text,expected_type,expected_confidence", [
        ("Brown v. Board, 347 U.S. 483 (1954)", "case", 0.95),
        ("42 U.S.C. § 12112", "statute", 0.90),
        ("Fed. R. Civ. P. 56", "regulation", 0.85),
        ("U.S. Const. Amend. XIV", "constitution", 0.92),
    ])
    def test_citation_type_detection(self, citation_text, expected_type, expected_confidence):
        """Test accurate detection of different citation types"""
        extracted = self.extractor.extract_citations_from_text(
            f"See {citation_text} for more details.", "test_para"
        )
        
        assert len(extracted) == 1
        citation = extracted[0]
        assert citation.citation_type == expected_type
        assert citation.confidence >= expected_confidence
    
    def test_citation_normalization(self):
        """Test citation text normalization"""
        test_variations = [
            ("Brown v Board", "Brown v. Board"),
            ("347 US 483", "347 U.S. 483"),
            ("42 USC 12112", "42 U.S.C. § 12112"),
        ]
        
        for input_text, expected_normalized in test_variations:
            extracted = self.extractor.extract_citations_from_text(input_text, "test")
            if extracted:
                assert expected_normalized in extracted[0].normalized_text
    
    def test_evidence_span_accuracy(self):
        """Test that evidence spans accurately capture citation locations"""
        text = "The Court in Brown v. Board, 347 U.S. 483 (1954), held that separate educational facilities are inherently unequal."
        
        citations = self.extractor.extract_citations_from_text(text, "test")
        
        assert len(citations) >= 1
        citation = citations[0]
        evidence_span = citation.evidence_span
        
        # Verify span captures the citation
        extracted_text = text[evidence_span["start"]:evidence_span["end"]]
        assert "Brown v. Board" in extracted_text
        assert "347 U.S. 483" in extracted_text
    
    @pytest.mark.performance
    def test_citation_extraction_performance(self):
        """Test performance of citation extraction on large documents"""
        # Generate large test document with citations
        large_document = self._generate_large_case_document(50000)  # 50k characters
        
        start_time = time.time()
        citations = self.extractor.extract_citations_from_text(
            large_document.text, large_document.para_id
        )
        end_time = time.time()
        
        extraction_time = end_time - start_time
        
        # Performance assertions
        assert extraction_time < 2.0, f"Extraction took {extraction_time:.2f}s, too slow"
        assert len(citations) > 0, "Should find citations in large document"
        
        # Memory usage check
        memory_usage = self._measure_memory_usage(
            lambda: self.extractor.extract_citations_from_text(large_document.text, large_document.para_id)
        )
        assert memory_usage < 100 * 1024 * 1024, f"Memory usage {memory_usage} bytes too high"
```

### Relationship Extraction Tests

```python
# tests/unit/test_relationship_extraction.py
class TestRelationshipExtraction:
    """Unit tests for case relationship extraction"""
    
    def setup_method(self):
        self.extractor = CaseRelationshipExtractor(self._get_test_config())
        self.test_relationships = self._load_relationship_test_cases()
    
    @pytest.mark.parametrize("relationship_text,expected_type,expected_confidence", [
        ("This court expressly overrules Smith v. Jones", "overrules", 0.9),
        ("We distinguish the instant case from Brown v. Board", "distinguishes", 0.8),
        ("Following the reasoning in Miranda v. Arizona", "follows", 0.85),
        ("In disagreement with the holding in Plessy v. Ferguson", "disagrees", 0.75),
    ])
    def test_relationship_pattern_detection(self, relationship_text, expected_type, expected_confidence):
        """Test detection of different case relationship types"""
        paragraphs = [self._create_test_paragraph(relationship_text)]
        
        relationships = self.extractor.extract_case_relationships("test_case", paragraphs)
        
        assert len(relationships) >= 1
        relationship = relationships[0]
        assert relationship.relationship_type == expected_type
        assert relationship.confidence >= expected_confidence
    
    def test_temporal_validation(self):
        """Test that temporal validation prevents invalid relationships"""
        # Create cases with known dates
        older_case = self._create_test_case("older_case", decision_date="1954-05-17")
        newer_case = self._create_test_case("newer_case", decision_date="2020-06-15")
        
        # Test overruling relationship (newer overrules older - valid)
        valid_overruling = CaseRelationship(
            source_case_id="newer_case",
            target_case_id="older_case", 
            relationship_type="overrules"
        )
        
        validation_result = self.extractor._validate_temporal_relationship(
            valid_overruling, newer_case, older_case
        )
        assert validation_result.valid
        
        # Test invalid overruling relationship (older overrules newer - invalid)
        invalid_overruling = CaseRelationship(
            source_case_id="older_case",
            target_case_id="newer_case",
            relationship_type="overrules"
        )
        
        validation_result = self.extractor._validate_temporal_relationship(
            invalid_overruling, older_case, newer_case
        )
        assert not validation_result.valid
```

### Temporal Reasoning Tests

```python
# tests/unit/test_temporal_reasoning.py
class TestTemporalReasoning:
    """Unit tests for temporal precedent reasoning"""
    
    def setup_method(self):
        self.temporal_reasoner = TemporalReasoner(self._get_test_config())
    
    def test_precedent_temporal_validity(self):
        """Test temporal validity of precedent relationships"""
        # Create test cases with different dates
        precedent_case = self._create_test_case("precedent", decision_date="1973-05-14")  # McDonnell Douglas
        citing_case = self._create_test_case("citing", decision_date="2020-06-15")      # Recent case
        
        evaluation = self.temporal_reasoner.evaluate_temporal_relationship(
            precedent_case, citing_case, "follows"
        )
        
        assert evaluation.valid
        assert evaluation.temporal_distance > 0  # Precedent is older
        assert evaluation.temporal_strength > 0.5  # Still relevant
    
    def test_staleness_calculation(self):
        """Test that very old precedents have reduced weight"""
        # Very old case (19th century)
        ancient_case = self._create_test_case("ancient", decision_date="1850-01-01")
        modern_case = self._create_test_case("modern", decision_date="2024-01-01")
        
        evaluation = self.temporal_reasoner.evaluate_temporal_relationship(
            ancient_case, modern_case, "follows"
        )
        
        assert evaluation.valid  # Still valid as precedent
        assert evaluation.temporal_strength < 0.8  # But with reduced strength due to age
        
        # Recent case should have higher strength
        recent_case = self._create_test_case("recent", decision_date="2020-01-01")
        recent_evaluation = self.temporal_reasoner.evaluate_temporal_relationship(
            recent_case, modern_case, "follows"
        )
        
        assert recent_evaluation.temporal_strength > evaluation.temporal_strength
    
    def test_contemporaneous_cases(self):
        """Test handling of cases decided around the same time"""
        case1 = self._create_test_case("case1", decision_date="2020-06-01")
        case2 = self._create_test_case("case2", decision_date="2020-06-15")
        
        evaluation = self.temporal_reasoner.evaluate_temporal_relationship(
            case1, case2, "follows"
        )
        
        # Contemporaneous cases should have special handling
        assert evaluation.valid
        assert "contemporaneous" in [rule.id for rule in evaluation.applicable_rules]
```

## 🔗 Integration Testing

### End-to-End Processing Tests

```python
# tests/integration/test_end_to_end_processing.py
class TestEndToEndProcessing:
    """Integration tests for complete caselaw processing pipeline"""
    
    def setup_method(self):
        self.plugin = CaselawPlugin(self._get_integration_test_config())
        self.test_dataset = self._load_integration_dataset()
        
    def test_complete_case_processing_pipeline(self):
        """Test complete pipeline from HF data to queryable hypergraph"""
        # Take sample of cases from test dataset
        sample_cases = self.test_dataset.get_sample(1000)
        
        # Process through complete pipeline
        processing_start = time.time()
        
        processed_results = []
        for case_batch in self._batch_cases(sample_cases, batch_size=100):
            result = self.plugin._process_case_batch(case_batch)
            processed_results.append(result)
            
        processing_end = time.time()
        
        # Verify processing completed successfully
        total_cases = sum(len(r.cases) for r in processed_results)
        assert total_cases == len(sample_cases), "Not all cases were processed"
        
        # Verify processing time is reasonable
        processing_time = processing_end - processing_start
        cases_per_second = total_cases / processing_time
        assert cases_per_second >= 10, f"Processing rate {cases_per_second:.2f} cases/sec too slow"
        
        # Verify entities were extracted
        total_entities = sum(len(r.nodes) for r in processed_results)
        assert total_entities > total_cases * 5, "Not enough entities extracted per case"
        
        # Verify relationships were extracted
        total_relationships = sum(len(r.edges) for r in processed_results)
        assert total_relationships > total_cases * 2, "Not enough relationships extracted per case"
    
    def test_cross_plugin_integration(self):
        """Test integration with employment law plugin"""
        # Load both plugins
        employment_plugin = self._load_employment_plugin()
        composition_manager = PluginCompositionManager(None)
        
        composition_manager.register_plugin("employment_law", employment_plugin)
        composition_manager.register_plugin("caselaw_access_project", self.plugin)
        
        # Test document that should trigger both plugins
        test_document = """
        Employee Jane Smith filed discrimination complaint citing hostile work environment.
        Court cited Burlington Industries v. Ellerth, 524 U.S. 742 (1998) regarding
        employer liability for supervisor harassment.
        """
        
        result = composition_manager.execute_cross_plugin_reasoning(
            "employment_law",
            {"text": test_document, "context": Context(jurisdiction="US")}
        )
        
        # Verify employment analysis was enhanced with caselaw
        assert result.primary_plugin == "employment_law"
        assert "caselaw_access_project" in result.enhancements
        
        caselaw_enhancements = result.enhancements["caselaw_access_project"]
        assert len(caselaw_enhancements.supporting_precedents) > 0
        
        # Verify Burlington Industries case was identified as relevant precedent
        precedent_citations = [p.citation for p in caselaw_enhancements.supporting_precedents]
        assert any("Burlington Industries" in cite for cite in precedent_citations)
```

## ⚡ Performance Testing

### Large-Scale Processing Tests

```python
# tests/performance/test_large_scale_processing.py
class TestLargeScaleProcessing:
    """Performance tests for large-scale caselaw processing"""
    
    def setup_method(self):
        self.plugin = CaselawPlugin(self._get_performance_test_config())
        self.performance_dataset = self._load_performance_dataset()
        
    @pytest.mark.slow
    def test_million_case_ingestion(self):
        """Test ingestion of 1M cases for performance characteristics"""
        cases = self.performance_dataset.get_cases(1000000)
        
        # Track key performance metrics
        metrics = PerformanceMetrics()
        
        ingestion_start = time.time()
        memory_start = psutil.Process().memory_info().rss
        
        batch_size = 10000
        processed_count = 0
        
        for case_batch in self._batch_cases(cases, batch_size):
            batch_start = time.time()
            
            # Process batch
            self.plugin.store.add_case_batch(case_batch)
            processed_count += len(case_batch)
            
            batch_end = time.time()
            
            # Track metrics
            batch_time = batch_end - batch_start
            memory_current = psutil.Process().memory_info().rss
            
            metrics.add_batch_metrics(
                batch_size=len(case_batch),
                processing_time=batch_time,
                memory_usage=memory_current,
                cases_processed=processed_count
            )
            
            # Log progress
            if processed_count % 100000 == 0:
                logger.info(f"Processed {processed_count} cases")
        
        ingestion_end = time.time()
        memory_end = psutil.Process().memory_info().rss
        
        # Analyze performance
        total_time = ingestion_end - ingestion_start
        total_memory = memory_end - memory_start
        
        cases_per_second = processed_count / total_time
        memory_per_case = total_memory / processed_count
        
        # Performance assertions
        assert cases_per_second >= 500, f"Ingestion rate {cases_per_second:.1f} cases/sec too slow"
        assert memory_per_case <= 1024, f"Memory usage {memory_per_case} bytes/case too high"
        
        # Memory should not grow linearly with case count (should be bounded)
        memory_growth_mb = total_memory / (1024 * 1024)
        assert memory_growth_mb <= 8192, f"Memory growth {memory_growth_mb:.1f}MB too high"
    
    @pytest.mark.concurrent
    def test_concurrent_query_performance(self):
        """Test concurrent query performance under load"""
        # Pre-populate with test data
        self._populate_test_data(100000)  # 100k cases
        
        # Define concurrent query workload
        query_types = [
            ("citation_lookup", lambda: self.plugin.store.resolve_citation("347 U.S. 483")),
            ("precedent_search", lambda: self.plugin.query_precedents(
                PrecedentQuery(legal_concept="discrimination", jurisdiction="US", limit=10)
            )),
            ("full_text_search", lambda: self.plugin.store.full_text_search("hostile environment", "US", 20)),
            ("authority_hierarchy", lambda: self.plugin.provenance_api.query_authority_hierarchy(
                "employment discrimination", "US"
            ))
        ]
        
        # Run concurrent queries
        concurrent_users = 50
        queries_per_user = 20
        
        def user_workload(user_id: int) -> List[float]:
            """Simulate user query workload"""
            query_times = []
            
            for _ in range(queries_per_user):
                query_type, query_func = random.choice(query_types)
                
                start_time = time.time()
                try:
                    result = query_func()
                    end_time = time.time()
                    query_times.append(end_time - start_time)
                except Exception as e:
                    logger.error(f"Query failed for user {user_id}: {e}")
                    query_times.append(float('inf'))
            
            return query_times
        
        # Execute concurrent workload
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(user_workload, user_id) 
                for user_id in range(concurrent_users)
            ]
            
            all_query_times = []
            for future in futures:
                user_times = future.result()
                all_query_times.extend(user_times)
        
        # Analyze performance
        valid_times = [t for t in all_query_times if t != float('inf')]
        
        avg_query_time = statistics.mean(valid_times)
        p95_query_time = statistics.quantiles(valid_times, n=20)[18]  # 95th percentile
        success_rate = len(valid_times) / len(all_query_times)
        
        # Performance assertions
        assert success_rate >= 0.98, f"Query success rate {success_rate:.3f} too low"
        assert avg_query_time <= 2.0, f"Average query time {avg_query_time:.2f}s too high"
        assert p95_query_time <= 5.0, f"95th percentile query time {p95_query_time:.2f}s too high"
```

## 📊 Data Quality Testing

### Citation Resolution Quality Tests

```python
# tests/quality/test_citation_resolution_quality.py
class TestCitationResolutionQuality:
    """Tests for citation resolution accuracy and quality"""
    
    def setup_method(self):
        self.plugin = CaselawPlugin(self._get_quality_test_config())
        self.quality_dataset = self._load_quality_test_dataset()
        
    def test_citation_resolution_accuracy(self):
        """Test accuracy of citation resolution across different formats"""
        citation_test_cases = self.quality_dataset.get_citation_test_cases()
        
        resolution_quality = CitationQualityMetrics()
        
        for test_case in citation_test_cases:
            citation_text = test_case.citation_text
            expected_case_id = test_case.expected_case_id
            
            # Extract and resolve citation
            extracted_citations = self.plugin.citation_extractor.extract_citations_from_text(
                citation_text, "test_para"
            )
            
            if not extracted_citations:
                resolution_quality.add_result("no_extraction", citation_text)
                continue
            
            citation = extracted_citations[0]
            candidates = self.plugin.citation_extractor.resolver.resolve_citation(citation, {})
            
            if not candidates:
                resolution_quality.add_result("no_resolution", citation_text)
                continue
            
            best_candidate = candidates[0]
            
            if best_candidate.target_id == expected_case_id:
                resolution_quality.add_result("correct", citation_text, best_candidate.confidence)
            else:
                resolution_quality.add_result("incorrect", citation_text, best_candidate.confidence)
        
        # Analyze quality metrics
        quality_report = resolution_quality.generate_report()
        
        assert quality_report.accuracy >= 0.90, f"Citation resolution accuracy {quality_report.accuracy:.3f} too low"
        assert quality_report.coverage >= 0.95, f"Citation coverage {quality_report.coverage:.3f} too low"
        assert quality_report.avg_confidence >= 0.80, f"Average confidence {quality_report.avg_confidence:.3f} too low"
    
    def test_cross_reference_consistency(self):
        """Test consistency of cross-references between cases"""
        # Get a sample of cases with known citations
        test_cases = self.quality_dataset.get_cross_reference_test_cases()
        
        consistency_errors = []
        
        for test_case in test_cases:
            source_case_id = test_case.source_case_id
            expected_targets = set(test_case.expected_citation_targets)
            
            # Extract actual citations from source case
            source_case = self.plugin.store.get_case(source_case_id)
            if not source_case:
                continue
            
            citation_edges = self.plugin.store.get_outgoing_edges(source_case_id)
            actual_targets = set()
            
            for edge in citation_edges:
                if edge.relation == "cites_case":
                    actual_targets.update(edge.heads)
            
            # Check for missing citations
            missing_citations = expected_targets - actual_targets
            if missing_citations:
                consistency_errors.append({
                    "type": "missing_citations",
                    "source_case": source_case_id,
                    "missing": list(missing_citations)
                })
            
            # Check for spurious citations
            spurious_citations = actual_targets - expected_targets
            if spurious_citations:
                consistency_errors.append({
                    "type": "spurious_citations",
                    "source_case": source_case_id,
                    "spurious": list(spurious_citations)
                })
        
        # Analyze consistency
        error_rate = len(consistency_errors) / len(test_cases)
        assert error_rate <= 0.05, f"Cross-reference error rate {error_rate:.3f} too high"
```

## 🧬 Property-Based Testing

### Legal Reasoning Invariants

```python
# tests/property/test_legal_reasoning_properties.py
from hypothesis import given, strategies as st

class TestLegalReasoningProperties:
    """Property-based tests for legal reasoning invariants"""
    
    def setup_method(self):
        self.plugin = CaselawPlugin(self._get_property_test_config())
    
    @given(
        source_date=st.dates(min_value=date(1800, 1, 1), max_value=date(2024, 12, 31)),
        target_date=st.dates(min_value=date(1800, 1, 1), max_value=date(2024, 12, 31))
    )
    def test_temporal_precedence_transitivity(self, source_date: date, target_date: date):
        """Property: If A precedes B and B precedes C, then A precedes C"""
        # Create three test cases with the given dates
        case_a = self._create_test_case("case_a", source_date)
        case_b = self._create_test_case("case_b", target_date)
        case_c = self._create_test_case("case_c", target_date + timedelta(days=1))
        
        # Test transitivity property
        if source_date < target_date:  # A precedes B
            eval_ab = self.plugin.temporal_reasoner.evaluate_temporal_relationship(
                case_a, case_b, "follows"
            )
            eval_bc = self.plugin.temporal_reasoner.evaluate_temporal_relationship(
                case_b, case_c, "follows"
            )
            eval_ac = self.plugin.temporal_reasoner.evaluate_temporal_relationship(
                case_a, case_c, "follows"
            )
            
            # If A→B and B→C are valid, then A→C should be valid
            if eval_ab.valid and eval_bc.valid:
                assert eval_ac.valid, "Temporal precedence transitivity violated"
    
    @given(
        authority_level=st.integers(min_value=1, max_value=1000),
        jurisdiction=st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_authority_hierarchy_monotonicity(self, authority_level: int, jurisdiction: str):
        """Property: Higher authority courts have higher binding strength"""
        # Create courts with different authority levels
        lower_court = self._create_test_court(jurisdiction, authority_level)
        higher_court = self._create_test_court(jurisdiction, authority_level + 100)
        
        case_lower = self._create_test_case_with_court("case_lower", lower_court)
        case_higher = self._create_test_case_with_court("case_higher", higher_court)
        
        query_context = Context(jurisdiction=jurisdiction)
        
        # Evaluate authority relationships
        eval_lower = self.plugin.jurisdictional_reasoner.evaluate_jurisdictional_authority(
            case_lower, case_lower, query_context
        )
        eval_higher = self.plugin.jurisdictional_reasoner.evaluate_jurisdictional_authority(
            case_higher, case_lower, query_context
        )
        
        # Higher authority should have higher or equal binding strength
        assert eval_higher.binding_strength >= eval_lower.binding_strength, \
            "Authority hierarchy monotonicity violated"
    
    @given(st.text(min_size=10, max_size=1000))
    def test_citation_extraction_idempotency(self, text: str):
        """Property: Re-extracting citations from the same text yields same results"""
        # Extract citations twice
        citations_1 = self.plugin.citation_extractor.extract_citations_from_text(text, "test_para")
        citations_2 = self.plugin.citation_extractor.extract_citations_from_text(text, "test_para")
        
        # Results should be identical
        assert len(citations_1) == len(citations_2), "Citation extraction not idempotent"
        
        for i, (c1, c2) in enumerate(zip(citations_1, citations_2)):
            assert c1.normalized_text == c2.normalized_text, f"Citation {i} differs between extractions"
            assert c1.evidence_span == c2.evidence_span, f"Citation {i} span differs between extractions"
```

## 🔒 Security Testing

### Vulnerability Assessment

```python
# tests/security/test_security_vulnerabilities.py
class TestSecurityVulnerabilities:
    """Security tests for the caselaw plugin"""
    
    def setup_method(self):
        self.plugin = CaselawPlugin(self._get_security_test_config())
        self.api_client = self._create_test_api_client()
    
    def test_sql_injection_prevention(self):
        """Test that API endpoints are protected against SQL injection"""
        injection_payloads = [
            "'; DROP TABLE cases; --",
            "' OR 1=1; --",
            "' UNION SELECT * FROM users; --",
            "\"; DROP TABLE hyperedges; --"
        ]
        
        for payload in injection_payloads:
            # Test various API endpoints with injection payloads
            with pytest.raises((ValueError, ValidationError, HTTPException)):
                self.api_client.get(f"/api/v1/cases/{payload}")
            
            with pytest.raises((ValueError, ValidationError, HTTPException)):
                self.api_client.post("/api/v1/search/retrieve", json={
                    "query": payload,
                    "jurisdiction": "US"
                })
    
    def test_input_validation(self):
        """Test input validation for all API endpoints"""
        invalid_inputs = [
            {"type": "oversized_query", "data": "a" * 1000000},  # 1MB query
            {"type": "malformed_json", "data": '{"invalid": json}'},
            {"type": "null_injection", "data": "\x00\x01\x02"},
            {"type": "script_injection", "data": "<script>alert('xss')</script>"}
        ]
        
        for invalid_input in invalid_inputs:
            # Test that invalid inputs are properly rejected
            response = self.api_client.post("/api/v1/search/retrieve", 
                                          json={"query": invalid_input["data"]})
            assert response.status_code in [400, 422], f"Failed to reject {invalid_input['type']}"
    
    def test_rate_limiting(self):
        """Test that rate limiting is properly enforced"""
        # Make requests rapidly to trigger rate limiting
        responses = []
        for i in range(100):  # Exceed typical rate limits
            response = self.api_client.get("/api/v1/health")
            responses.append(response)
        
        # Should see rate limiting after some requests
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0, "Rate limiting not enforced"
    
    def test_authentication_enforcement(self):
        """Test that authentication is properly enforced"""
        # Test without authentication
        unauthenticated_client = self._create_unauthenticated_client()
        
        protected_endpoints = [
            "/api/v1/provenance/trace/cap:12345",
            "/api/v1/search/retrieve",
            "/api/v1/citations/resolve"
        ]
        
        for endpoint in protected_endpoints:
            response = unauthenticated_client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} not properly protected"
```

## 📈 Test Data Management

### Test Dataset Generation

```python
# tests/data/test_data_generator.py
class TestDataGenerator:
    """Generate synthetic test data for comprehensive testing"""
    
    def __init__(self):
        self.faker = Faker()
        self.legal_terms = self._load_legal_vocabulary()
        self.citation_patterns = self._load_citation_patterns()
    
    def generate_synthetic_case(self, case_id: str, **kwargs) -> Dict[str, Any]:
        """Generate a synthetic case document"""
        return {
            "id": case_id,
            "name": self._generate_case_name(),
            "decision_date": kwargs.get("decision_date", self.faker.date_between(start_date="-50y", end_date="today")),
            "court": self._generate_court_info(kwargs.get("jurisdiction", "US")),
            "jurisdiction": kwargs.get("jurisdiction", "US"),
            "casebody": {
                "opinions": [
                    {
                        "type": "majority",
                        "author": self.faker.name(),
                        "text": self._generate_opinion_text(kwargs.get("legal_concepts", []))
                    }
                ]
            },
            "citations": self._generate_citations(),
            "cites_to": kwargs.get("cites_to", [])
        }
    
    def _generate_opinion_text(self, legal_concepts: List[str]) -> str:
        """Generate realistic legal opinion text"""
        paragraphs = []
        
        # Generate introduction
        paragraphs.append(self._generate_intro_paragraph())
        
        # Generate legal analysis paragraphs
        for concept in legal_concepts:
            paragraphs.append(self._generate_legal_analysis_paragraph(concept))
        
        # Generate conclusion
        paragraphs.append(self._generate_conclusion_paragraph())
        
        return "\n\n".join(paragraphs)
    
    def generate_citation_test_cases(self, count: int) -> List[Dict[str, Any]]:
        """Generate test cases for citation extraction testing"""
        test_cases = []
        
        for i in range(count):
            # Generate various citation formats
            citation_type = random.choice(["case", "statute", "regulation", "constitution"])
            
            if citation_type == "case":
                citation_text = f"{self.faker.last_name()} v. {self.faker.last_name()}, {random.randint(100, 999)} U.S. {random.randint(1, 999)} ({random.randint(1950, 2024)})"
            elif citation_type == "statute":
                citation_text = f"{random.randint(1, 50)} U.S.C. § {random.randint(1, 9999)}"
            elif citation_type == "regulation":
                citation_text = f"{random.randint(1, 50)} C.F.R. § {random.randint(1, 999)}.{random.randint(1, 99)}"
            else:  # constitution
                citation_text = f"U.S. Const. Amend. {random.choice(['I', 'IV', 'V', 'VI', 'XIV'])}"
            
            test_case = {
                "id": f"citation_test_{i}",
                "citation_text": citation_text,
                "expected_type": citation_type,
                "context": self._generate_citation_context(citation_text),
                "expected_confidence": random.uniform(0.8, 1.0)
            }
            
            test_cases.append(test_case)
        
        return test_cases
```

## 🎯 Test Execution Strategy

### Continuous Integration Pipeline

```yaml
# .github/workflows/caselaw_plugin_tests.yml
name: CAP Caselaw Plugin Tests

on:
  push:
    branches: [main, develop]
    paths: ['plugins/caselaw/**']
  pull_request:
    branches: [main]
    paths: ['plugins/caselaw/**']

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .[test]
        pip install -e .[nlp]
    
    - name: Run unit tests
      run: |
        pytest tests/unit/caselaw/ -v --cov=plugins.caselaw --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: caselaw_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -e .[test,nlp]
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost:5432/caselaw_test
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest tests/integration/caselaw/ -v --maxfail=5

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -e .[test,nlp]
    
    - name: Run performance benchmarks
      run: |
        pytest tests/performance/caselaw/ -v --benchmark-only --benchmark-json=benchmark.json
    
    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        tool: 'pytest'
        output-file-path: benchmark.json
```

## 📊 Test Metrics & Reporting

### Quality Gates

```python
# tests/quality_gates.py
class QualityGates:
    """Define quality gates that must be met for release"""
    
    QUALITY_THRESHOLDS = {
        "unit_test_coverage": 0.90,
        "integration_test_coverage": 0.80,
        "citation_resolution_accuracy": 0.90,
        "relationship_detection_accuracy": 0.85,
        "performance_regression_threshold": 0.10,  # 10% slowdown max
        "memory_usage_limit": 8 * 1024 * 1024 * 1024,  # 8GB max
        "query_latency_p95": 2.0,  # 2 seconds max
        "ingestion_rate_minimum": 500  # cases per second
    }
    
    @classmethod
    def validate_release_readiness(cls, test_results: Dict[str, Any]) -> bool:
        """Validate that all quality gates are met"""
        failures = []
        
        for metric, threshold in cls.QUALITY_THRESHOLDS.items():
            if metric not in test_results:
                failures.append(f"Missing metric: {metric}")
                continue
            
            actual_value = test_results[metric]
            
            if "accuracy" in metric or "coverage" in metric:
                if actual_value < threshold:
                    failures.append(f"{metric}: {actual_value:.3f} < {threshold:.3f}")
            elif "latency" in metric or "usage" in metric:
                if actual_value > threshold:
                    failures.append(f"{metric}: {actual_value} > {threshold}")
            elif "rate" in metric:
                if actual_value < threshold:
                    failures.append(f"{metric}: {actual_value} < {threshold}")
        
        if failures:
            logger.error("Quality gate failures:")
            for failure in failures:
                logger.error(f"  - {failure}")
            return False
        
        logger.info("All quality gates passed!")
        return True
```

This comprehensive testing strategy ensures the CAP caselaw plugin meets the highest standards for accuracy, performance, and reliability when processing 37M+ legal documents with full provenance tracking.