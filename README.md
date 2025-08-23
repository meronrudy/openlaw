# Legal Hypergraph Analysis System

A provenance-first legal ontology hypergraph system for explainable AI-powered legal document analysis. This system provides comprehensive employment law analysis with transparent reasoning chains and confidence scoring.

## 🏗️ System Architecture

This system implements a **knowledge substrate** architecture where legal texts exist within a hypergraph structure, enabling complex legal reasoning with full provenance tracking for explainable AI.

### Core Components

- **Hypergraph Storage Engine**: SQLiteDict-based storage with efficient node/edge indexing
- **Plugin SDK**: Extensible architecture for domain-specific legal analysis
- **Rule Engine**: Forward-chaining inference with modus ponens-style legal reasoning
- **NLP Pipeline**: Legal entity recognition and citation extraction
- **Provenance Tracking**: Complete audit trails for all reasoning steps
- **CLI Interface**: Command-line tools for document analysis and batch processing

### Key Features

- ✅ **Explainable AI**: Every legal conclusion includes reasoning chains and confidence scores
- ✅ **Provenance-First**: Complete audit trails from source documents to final conclusions
- ✅ **Plugin Architecture**: Extensible domain-specific legal analysis modules
- ✅ **Employment Law Support**: ADA, FLSA, at-will employment, workers' compensation
- ✅ **Hypergraph Reasoning**: Complex legal relationships beyond simple graphs
- ✅ **Test-Driven Development**: 112 unit tests with comprehensive coverage

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd openlaw

# Install dependencies
pip install -e .

# Run tests to verify installation
python -m pytest tests/unit/ -v
```

### Basic Usage

```bash
# Analyze a single document
python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt

# Interactive demo
python cli_driver.py demo

# Batch analysis
python cli_driver.py batch --directory test_documents/employment_law/

# JSON output for integration
python cli_driver.py analyze --file document.txt --format json
```

## 📋 CLI Reference

### Commands

#### `analyze` - Single Document Analysis
```bash
python cli_driver.py analyze --file <path> [options]

Options:
  --format {summary,detailed,json}  Output format (default: summary)
  --jurisdiction JURISDICTION       Legal jurisdiction (default: US)
  --show-reasoning                  Include detailed reasoning steps
```

#### `demo` - Interactive Demo
```bash
python cli_driver.py demo

# Provides interactive document selection and analysis
# Demonstrates system capabilities with test documents
```

#### `batch` - Batch Processing
```bash
python cli_driver.py batch --directory <path> [options]

Options:
  --format {summary,detailed,json}  Output format (default: summary)
  --output-file FILE               Save results to JSON file
```

### Example Output

#### Summary Format
```
🔍 Analyzing document: ada_accommodation_request.txt
📄 Document length: 2,416 characters
⚖️  Jurisdiction: US

📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 13 total
   • ADA_REQUEST: 7
   • DISABILITY: 2
   • REASONABLE_ACCOMMODATION: 3

📚 Legal Citations: 1
   • 42 U.S.C. § 12112

⚖️  Legal Conclusions: 1
   • ADA_VIOLATION: Employer may be required to provide reasonable accommodation
     Legal Basis: 42 U.S.C. § 12112(b)(5)(A)
     Confidence: 85.0%
```

#### JSON Format
```json
{
  "document_path": "ada_accommodation_request.txt",
  "analysis_time": "2025-08-23T15:31:05.665134",
  "analysis_results": {
    "entities": [...],
    "citations": [...],
    "original_facts": [...],
    "derived_facts": [...],
    "conclusions": [...]
  }
}
```

## 🏛️ Employment Law Capabilities

The system currently supports comprehensive analysis of four major employment law areas:

### Americans with Disabilities Act (ADA)
- **Entities**: Disability types, accommodation requests, interactive process
- **Rules**: Reasonable accommodation requirements, undue hardship analysis
- **Citations**: 42 U.S.C. § 12112, relevant case law
- **Analysis**: Accommodation feasibility, employer obligations

### Fair Labor Standards Act (FLSA)
- **Entities**: Overtime violations, wage rates, hours worked
- **Rules**: 40-hour workweek, overtime calculations, exemptions
- **Citations**: 29 U.S.C. § 207, DOL regulations
- **Analysis**: Overtime entitlement, wage calculations

### At-Will Employment & Wrongful Termination
- **Entities**: Termination circumstances, public policy violations
- **Rules**: At-will exceptions, whistleblower protections
- **Citations**: State-specific wrongful termination statutes
- **Analysis**: Termination legality, public policy exceptions

### Workers' Compensation
- **Entities**: Workplace injuries, medical treatment, lost wages
- **Rules**: Compensability requirements, benefit calculations
- **Citations**: State workers' comp statutes
- **Analysis**: Claim validity, benefit entitlement

## 🔧 System Architecture Deep Dive

### Data Models

#### Core Entities
```python
# Node: Fundamental knowledge unit
class Node:
    id: str
    node_type: str
    attributes: Dict[str, Any]
    provenance: Provenance

# Hyperedge: Multi-way relationships
class Hyperedge:
    id: str
    relation: str
    tails: List[str]  # Input nodes
    heads: List[str]  # Output nodes
    provenance: Provenance

# Provenance: Complete audit trail
class Provenance:
    source: str
    timestamp: datetime
    confidence: float
    method: str
```

#### Legal Rules
```python
class LegalRule:
    id: str
    premises: List[str]      # Required conditions
    conclusion: str          # Legal conclusion
    authority: str          # Legal authority (statute, case)
    jurisdiction: str       # Geographic scope
    priority: int          # Conflict resolution
    context: Context       # Applicability conditions
```

### Plugin Architecture

The system uses a modular plugin architecture for domain-specific analysis:

```
plugins/
├── employment_law/
│   ├── __init__.py
│   ├── manifest.json      # Plugin metadata
│   ├── plugin.py         # Main plugin class
│   ├── ner.py           # Named Entity Recognition
│   ├── rules.py         # Legal rules
│   └── explainer.py     # Explanation generation
```

#### Plugin SDK Interfaces

```python
# Core plugin interfaces
class OntologyProvider(ABC):
    @abstractmethod
    def get_ontology(self) -> Dict[str, Any]: ...

class RuleProvider(ABC):
    @abstractmethod
    def get_rules(self, context: Context) -> List[LegalRule]: ...

class LegalExplainer(ABC):
    @abstractmethod
    def explain_conclusion(self, conclusion: Dict, 
                         reasoning_chain: List) -> str: ...
```

### Reasoning Engine

The system implements forward-chaining inference with legal-specific enhancements:

#### Features
- **Modus Ponens**: Classical logical inference
- **Confidence Propagation**: Bayesian-style confidence calculation
- **Conflict Resolution**: Authority hierarchy, specificity, temporal precedence
- **Context Sensitivity**: Jurisdiction and temporal applicability
- **Statement-Based Reasoning**: Natural language premise matching

#### Reasoning Process
1. **Fact Extraction**: Convert entities to logical statements
2. **Rule Application**: Forward-chaining inference
3. **Conflict Resolution**: Handle contradicting conclusions
4. **Explanation Generation**: Build reasoning chains
5. **Confidence Scoring**: Propagate and calculate confidence

### Storage Engine

Efficient hypergraph storage with SQLiteDict backend:

```python
# Persistent storage with indexing
class GraphStore:
    nodes: SQLiteDict        # Node storage
    edges: SQLiteDict        # Hyperedge storage
    node_index: Dict         # Type-based indexing
    edge_index: Dict         # Relation-based indexing
    incidence_index: Dict    # Node-edge relationships
```

## 🧪 Testing Strategy

Comprehensive test coverage with 112 unit tests:

### Test Structure
```
tests/
├── unit/                    # Unit tests (112 tests)
│   ├── test_core_models.py     # Data model validation
│   ├── test_storage.py         # Storage engine tests
│   ├── test_reasoning.py       # Rule engine tests
│   ├── test_plugin_sdk.py      # Plugin interface tests
│   ├── test_legal_nlp.py       # NLP pipeline tests
│   ├── test_employment_law_plugin.py  # Domain plugin tests
│   └── test_cli_driver.py      # CLI interface tests
└── fixtures/                # Test data and utilities
```

### Testing Approach
- **Test-Driven Development**: RED-GREEN-REFACTOR methodology
- **Comprehensive Coverage**: All core components and plugins
- **Legal Accuracy**: Domain-specific legal reasoning validation
- **Integration Testing**: End-to-end CLI workflow validation

### Running Tests
```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test categories
python -m pytest tests/unit/test_reasoning.py -v
python -m pytest tests/unit/test_employment_law_plugin.py -v

# Run CLI tests
python -m pytest tests/unit/test_cli_driver.py -v
```

## 📖 Plugin Development Guide

### Creating a New Legal Domain Plugin

1. **Create Plugin Structure**
```bash
mkdir plugins/new_domain
cd plugins/new_domain
touch __init__.py manifest.json plugin.py ner.py rules.py
```

2. **Define Plugin Manifest**
```json
{
  "id": "new_domain_law",
  "name": "New Domain Law Plugin",
  "version": "1.0.0",
  "description": "Legal analysis for new domain",
  "author": "Legal Tech Team",
  "capabilities": ["ner", "rules", "explainer"],
  "dependencies": [],
  "entry_point": "plugin.NewDomainPlugin"
}
```

3. **Implement Core Interfaces**
```python
from sdk.plugin import OntologyProvider, RuleProvider, LegalExplainer

class NewDomainPlugin(OntologyProvider, RuleProvider, LegalExplainer):
    def get_ontology(self) -> Dict[str, Any]:
        # Define domain-specific entities and relationships
        pass
    
    def get_rules(self, context: Context) -> List[LegalRule]:
        # Implement domain-specific legal rules
        pass
    
    def explain_conclusion(self, conclusion: Dict, 
                         reasoning_chain: List) -> str:
        # Generate human-readable explanations
        pass
```

4. **Develop NER Module**
```python
class NewDomainNER:
    def __init__(self):
        # Initialize domain-specific patterns
        self.patterns = {
            "DOMAIN_ENTITY": r"pattern_regex",
            # Add more patterns
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        # Implement entity extraction logic
        pass
```

5. **Define Legal Rules**
```python
class NewDomainRules:
    def get_all_rules(self) -> List[LegalRule]:
        return [
            LegalRule(
                id="rule_1",
                premises=["premise_1", "premise_2"],
                conclusion="legal_conclusion",
                authority="Legal Authority",
                jurisdiction="US",
                priority=1
            ),
            # Add more rules
        ]
```

### Plugin Testing

Create comprehensive tests for your plugin:

```python
class TestNewDomainPlugin:
    def test_entity_extraction(self):
        # Test NER functionality
        pass
    
    def test_rule_application(self):
        # Test legal reasoning
        pass
    
    def test_explanation_generation(self):
        # Test explanation quality
        pass
```

## 🔬 Research Applications

This system enables several research directions:

### Legal AI & Explainability
- **Transparent Legal AI**: Complete reasoning chain documentation
- **Confidence Quantification**: Bayesian confidence propagation
- **Bias Detection**: Systematic analysis of reasoning patterns

### Legal Informatics
- **Hypergraph Legal Modeling**: Beyond traditional graph structures
- **Provenance Tracking**: Complete audit trails for legal conclusions
- **Cross-Domain Reasoning**: Plugin-based extensibility

### Computational Law
- **Formal Legal Reasoning**: Logic-based rule representation
- **Automated Legal Analysis**: Large-scale document processing
- **Legal Knowledge Graphs**: Rich relationship modeling

## 🤝 Contributing

### Development Workflow

1. **Fork & Clone**
```bash
git clone <your-fork>
cd openlaw
```

2. **Set Up Development Environment**
```bash
pip install -e .[dev]
pre-commit install
```

3. **Create Feature Branch**
```bash
git checkout -b feature/new-feature
```

4. **Follow TDD Methodology**
```bash
# 1. Write failing test (RED)
python -m pytest tests/unit/test_new_feature.py -v

# 2. Implement minimal code (GREEN)
# Make tests pass

# 3. Refactor and improve (REFACTOR)
# Clean up implementation
```

5. **Submit Pull Request**
- Include comprehensive tests
- Update documentation
- Follow code style guidelines

### Code Standards

- **Python Style**: Follow PEP 8 with Black formatting
- **Type Hints**: Use comprehensive type annotations
- **Documentation**: Docstrings for all public APIs
- **Testing**: Maintain >90% test coverage

### Legal Domain Expertise

We welcome contributions from legal professionals:

- **Rule Validation**: Ensure legal accuracy
- **Test Case Development**: Create realistic legal scenarios
- **Domain Expansion**: Add new areas of law
- **Explanation Quality**: Improve AI explanations

## 📚 References & Related Work

### Legal AI & NLP
- **Legal Entity Recognition**: Chalkidis et al. (2019)
- **Legal Reasoning Systems**: Ashley & Rissland (1987)
- **Explainable AI in Law**: Zeleznikow & Stranieri (1995)

### Hypergraph Theory
- **Hypergraph Learning**: Feng et al. (2019)
- **Knowledge Hypergraphs**: Ding et al. (2020)

### Computational Law
- **Logic-Based Legal Systems**: Sergot et al. (1986)
- **Legal Ontologies**: Hoekstra et al. (2007)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support & Contact

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for general questions
- **Documentation**: Full API documentation in `/docs`
- **Examples**: Additional examples in `/examples`

---

**Built with ❤️ for the legal technology community**

*Advancing transparent, explainable AI for legal document analysis*