# Legal Hypergraph System - Comprehensive Test Suite

## Overview

This test suite provides comprehensive test-driven development support for the provenance-first legal hypergraph system, covering all user stories and system requirements with realistic legal scenarios.

## Test Suite Structure

### 📁 End-to-End Tests (`tests/e2e/`)

#### `test_legal_document_analysis.py` (396 lines)
**Coverage**: Legal Researcher, Legal Practitioner, In-House Counsel workflows

- **ADA Analysis Tests**: Complete accommodation request workflows with provenance tracking
- **FLSA Analysis Tests**: Overtime calculation and compliance validation
- **Workers Compensation Tests**: Causation chain analysis and liability determination
- **At-Will Employment Tests**: Wrongful termination and retaliation analysis
- **Cross-Domain Tests**: Multi-domain scenarios (ADA + FLSA)
- **Provenance Tracking Tests**: End-to-end provenance chain validation
- **Explanation Generation Tests**: Statutory and counterfactual explanations
- **Performance Tests**: Response time and concurrency requirements

#### `test_plugin_development.py` (563 lines)
**Coverage**: Domain Experts, Plugin Developers, Legal Technology Specialists

- **Plugin Creation Tests**: From-scratch plugin development workflows
- **Validation Framework Tests**: Legal rule and ontology validation
- **Security Tests**: Plugin sandboxing and resource limits
- **Integration Tests**: Version management and dependency resolution
- **Performance Tests**: Plugin loading and execution optimization

#### `test_system_integration.py` (439 lines)
**Coverage**: Business Stakeholders, Managing Partners, Legal Operations

- **ROI Measurement Tests**: Time savings, accuracy, and cost efficiency
- **Compliance Monitoring Tests**: Real-time compliance dashboards
- **Workflow Optimization Tests**: Bottleneck identification and resource allocation
- **Client Analytics Tests**: Client-facing insights and predictive outcomes

### 📁 Test Fixtures (`tests/fixtures/`)

#### `legal_documents.py` (246 lines)
**Realistic Legal Test Data**

- **Employment Law Scenarios**: ADA, FLSA, Workers Comp, At-Will
- **Multi-Domain Scenarios**: Complex cases spanning multiple legal areas
- **Citation-Heavy Documents**: Legal authority validation testing
- **Fact Patterns**: Targeted legal rule testing scenarios
- **Metadata Framework**: Expected outcomes and validation criteria

### 📁 Test Helpers (`tests/helpers/`)

#### `legal_assertions.py` (367 lines)
**Legal-Specific Validation**

- **Legal Assertions**: Entity types, provenance, legal authorities
- **Performance Assertions**: Response times, memory usage, concurrency
- **Security Assertions**: Data protection, access control, audit trails
- **Compliance Assertions**: GDPR, attorney-client privilege, retention policies

### 🔧 Test Configuration

#### `pytest.ini` (55 lines)
- Async testing configuration
- Comprehensive coverage reporting
- Performance monitoring and timeouts
- Legal domain test markers
- Security and compliance test categories

#### `conftest.py` (367 lines)
- Shared fixtures for all test modules
- System initialization and cleanup
- Mock NLP pipelines for testing
- Performance monitoring utilities
- Test data factories

## Test-Driven Development Features

### 🎯 User Story Mapping
Every test maps directly to specific user stories:

```python
async def test_ada_accommodation_complete_workflow(self, system, legal_context, legal_assertions):
    """
    Test Story: Legal Researcher - Document Analysis for ADA Compliance
    
    Given: A document describing an ADA accommodation scenario
    When: System analyzes the document and applies legal rules
    Then: System should identify legal obligations with complete provenance
    """
```

### ⚡ Performance Requirements
Built-in performance validation:

```python
# Business requirement: Analysis within 2 minutes for 10k word documents
performance_assertions.assert_response_time_acceptable(
    analysis_time, 120.0, "legal document analysis"
)

# Accuracy requirement: >85% for business justification
assert accuracy_rate >= 85, f"Accuracy rate {accuracy_rate:.1f}% below requirement"
```

### 🔒 Security & Compliance Testing
Comprehensive security validation:

```python
# Test attorney-client privilege protection
compliance_assertions.assert_attorney_client_privilege_maintained(
    access_log, privileged_docs
)

# Test plugin security sandboxing
security_assertions.assert_access_control_enforced(
    access_result, expected_access=False
)
```

### 📊 Legal Domain Expertise
Tests understand legal concepts:

```python
# Validate legal reasoning chains
legal_assertions.assert_reasoning_chain_complete(
    conclusion_id, derivation_chain
)

# Check proper legal citation formats
legal_assertions.assert_proper_citation_format(
    citation, citation_type='statute'
)
```

## Running the Test Suite

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m e2e                    # End-to-end tests
pytest -m ada                    # ADA-specific tests
pytest -m performance            # Performance tests
pytest -m security              # Security tests

# Run tests with coverage
pytest --cov=core --cov=sdk --cov=plugins

# Run tests in parallel
pytest -n auto
```

### Test Markers Available
- `e2e`: End-to-end workflow tests
- `integration`: Component integration tests
- `unit`: Individual component tests
- `performance`: Performance and scalability tests
- `security`: Security and compliance tests
- `ada`, `flsa`, `workers_comp`, `at_will`: Domain-specific tests
- `multi_domain`: Cross-domain scenario tests
- `slow`: Tests taking >30 seconds
- `plugin`: Plugin system tests
- `provenance`: Provenance tracking tests

### Performance Testing
```bash
# Run performance tests with timing
pytest -m performance --durations=10

# Run slow tests (>30 seconds)
pytest --runslow

# Monitor memory usage
pytest --memray
```

### Coverage Reporting
```bash
# Generate HTML coverage report
pytest --cov-report=html

# View coverage in terminal
pytest --cov-report=term-missing

# Generate XML coverage for CI
pytest --cov-report=xml
```

## Test Data Management

### Realistic Legal Scenarios
All test documents are based on realistic legal scenarios:

- **ADA Accommodation Request**: Complete accommodation scenario with all required elements
- **FLSA Overtime Violation**: Detailed work hours and wage calculations
- **Workers Compensation Claim**: Workplace injury with causation chain
- **At-Will Retaliation**: Protected activity and temporal relationship

### Expected Outcomes
Each test document includes expected outcomes:

```python
TEST_METADATA = {
    'ADA_ACCOMMODATION_REQUEST': {
        'expected_entities': ['Employee', 'Employer', 'Disability', 'AccommodationRequest'],
        'expected_obligations': ['provide_reasonable_accommodation'],
        'legal_authorities': ['42 U.S.C. § 12112'],
        'complexity_level': 'medium'
    }
}
```

### Validation Criteria
Comprehensive validation for legal accuracy:

- Entity extraction completeness
- Legal reasoning correctness
- Citation format compliance
- Provenance chain integrity
- Performance requirements
- Security and compliance standards

## Continuous Integration Support

### GitHub Actions Integration
```yaml
name: Legal Hypergraph Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov --junit-xml=test-results.xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### Quality Gates
- **Code Coverage**: >90% for core components
- **Performance**: All tests complete within timeout
- **Security**: No security violations detected
- **Legal Accuracy**: >85% accuracy on validation scenarios

## Test Environment Configuration

### Environment Variables
```bash
LEGAL_HYPERGRAPH_ENV=test
LEGAL_HYPERGRAPH_LOG_LEVEL=WARNING
LEGAL_HYPERGRAPH_PLUGIN_DIR=tests/fixtures/plugins
LEGAL_HYPERGRAPH_DISABLE_TELEMETRY=true
```

### Mock Dependencies
- **NLP Models**: Mocked for fast testing without ML dependencies
- **External APIs**: Mocked legal database connections
- **Network Access**: Disabled in plugin sandboxes
- **File System**: Restricted access for security testing

## Benefits for Development

### 🚀 Test-Driven Development
- Clear requirements through test specifications
- Immediate feedback on implementation progress
- Regression detection for code changes
- Documentation through executable examples

### 📈 Quality Assurance
- Comprehensive coverage of user scenarios
- Performance benchmarking built-in
- Security validation automated
- Legal accuracy verification

### 🔧 Development Productivity
- Fast feedback loops with focused test execution
- Clear failure diagnostics with legal context
- Automated setup and teardown of test environments
- Realistic test data for development

### 📊 Business Validation
- ROI measurement validation
- Compliance monitoring verification
- Client value demonstration
- Performance requirement validation

This comprehensive test suite provides everything needed for test-driven development of the legal hypergraph system, ensuring both technical correctness and legal accuracy while supporting all user scenarios from individual legal researchers to enterprise deployments.