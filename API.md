# Legal Hypergraph Analysis System - API Documentation

This document provides comprehensive API documentation for all system components.

## 📋 Table of Contents

- [Core Models](#core-models)
- [Storage Engine](#storage-engine)
- [Rule Engine](#rule-engine)
- [Plugin SDK](#plugin-sdk)
- [NLP Pipeline](#nlp-pipeline)
- [CLI Interface](#cli-interface)
- [Employment Law Plugin](#employment-law-plugin)

## Core Models

### Node

Represents a fundamental knowledge unit in the hypergraph.

```python
from core.model import Node, Provenance

class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
```

#### Methods

##### `__init__(node_type: str, attributes: Dict[str, Any], provenance: Provenance) -> Node`

Creates a new Node instance.

**Parameters:**
- `node_type`: Type classification for the node
- `attributes`: Key-value pairs containing node data
- `provenance`: Provenance information for audit trail

**Example:**
```python
from datetime import datetime

provenance = Provenance(
    source="document.txt",
    timestamp=datetime.now(),
    confidence=0.85,
    method="NER_extraction"
)

node = Node(
    node_type="LEGAL_ENTITY",
    attributes={
        "text": "reasonable accommodation",
        "entity_type": "ADA_REQUEST"
    },
    provenance=provenance
)
```

### Hyperedge

Represents multi-way relationships between nodes.

```python
class Hyperedge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    relation: str
    tails: List[str] = Field(min_length=1)  # Input nodes
    heads: List[str] = Field(min_length=1)  # Output nodes
    attributes: Dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
```

#### Methods

##### `__init__(relation: str, tails: List[str], heads: List[str], provenance: Provenance) -> Hyperedge`

Creates a new Hyperedge instance.

**Parameters:**
- `relation`: Type of relationship
- `tails`: List of input node IDs
- `heads`: List of output node IDs
- `provenance`: Provenance information

**Example:**
```python
edge = Hyperedge(
    relation="IMPLIES",
    tails=["premise_node_1", "premise_node_2"],
    heads=["conclusion_node"],
    provenance=provenance
)
```

### Provenance

Tracks the origin and reliability of information.

```python
class Provenance(BaseModel):
    source: str = Field(min_length=1)
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    method: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### Validation

- `source`: Must be non-empty string
- `confidence`: Must be between 0.0 and 1.0
- `timestamp`: Must be valid datetime
- `method`: Description of how information was derived

### Context

Defines applicability conditions for rules and analysis.

```python
class Context(BaseModel):
    jurisdiction: str = "US"
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    law_type: str = "general"
    authority_level: Optional[str] = None
```

#### Methods

##### `is_applicable(jurisdiction: str, date: datetime, law_type: str) -> bool`

Checks if context applies to given conditions.

**Example:**
```python
context = Context(
    jurisdiction="US",
    law_type="employment",
    valid_from=datetime(2024, 1, 1)
)

is_valid = context.is_applicable("US", datetime.now(), "employment")
```

### Helper Functions

##### `mk_node(node_type: str, **attributes) -> Node`

Convenience function for creating nodes with auto-generated provenance.

##### `mk_edge(relation: str, tails: List[str], heads: List[str]) -> Hyperedge`

Convenience function for creating hyperedges.

## Storage Engine

### GraphStore

Persistent hypergraph storage with efficient indexing.

```python
from core.storage import GraphStore

class GraphStore:
    def __init__(self, storage_path: Optional[str] = None)
```

#### Methods

##### `add_node(node: Node) -> str`

Adds a node to the store and returns its ID.

**Parameters:**
- `node`: Node instance to store

**Returns:** Node ID

**Example:**
```python
store = GraphStore("legal_graph.db")
node_id = store.add_node(node)
```

##### `add_edge(edge: Hyperedge) -> str`

Adds a hyperedge to the store.

**Parameters:**
- `edge`: Hyperedge instance to store

**Returns:** Edge ID

##### `get_node(node_id: str) -> Optional[Node]`

Retrieves a node by ID.

##### `get_edge(edge_id: str) -> Optional[Hyperedge]`

Retrieves a hyperedge by ID.

##### `query_nodes(node_type: Optional[str] = None, **filters) -> List[Node]`

Queries nodes with optional filtering.

**Parameters:**
- `node_type`: Filter by node type
- `**filters`: Additional attribute filters

**Example:**
```python
# Find all legal entities
entities = store.query_nodes(node_type="LEGAL_ENTITY")

# Find ADA-related entities
ada_entities = store.query_nodes(
    node_type="LEGAL_ENTITY",
    entity_type="ADA_REQUEST"
)
```

##### `query_edges(relation: Optional[str] = None, **filters) -> List[Hyperedge]`

Queries hyperedges with optional filtering.

##### `get_incoming_edges(node_id: str) -> List[Hyperedge]`

Gets all edges where the node is in heads.

##### `get_outgoing_edges(node_id: str) -> List[Hyperedge]`

Gets all edges where the node is in tails.

##### `clear() -> None`

Removes all nodes and edges from the store.

## Rule Engine

### LegalRule

Represents a legal rule for automated reasoning.

```python
from core.rules import LegalRule

class LegalRule(BaseModel):
    id: str
    premises: List[str]
    conclusion: str
    authority: str
    jurisdiction: str = "US"
    priority: int = 1
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    context: Context = Field(default_factory=Context)
```

#### Methods

##### `to_hyperedge(store: GraphStore) -> Hyperedge`

Converts the rule to a hyperedge representation.

##### `is_applicable(context: Context) -> bool`

Checks if rule applies in given context.

**Example:**
```python
rule = LegalRule(
    id="ada_accommodation_rule",
    premises=["employee_has_disability", "can_perform_essential_functions"],
    conclusion="reasonable_accommodation_required",
    authority="42 U.S.C. § 12112(b)(5)(A)",
    priority=1
)

# Convert to hyperedge
edge = rule.to_hyperedge(store)
```

### RuleEngine

Forward-chaining inference engine for legal reasoning.

```python
from core.reasoning import RuleEngine

class RuleEngine:
    def __init__(self, store: GraphStore)
```

#### Methods

##### `apply_rules(rules: List[LegalRule], context: Context) -> List[Node]`

Applies rules using forward-chaining inference.

**Parameters:**
- `rules`: List of legal rules to apply
- `context`: Context for rule application

**Returns:** List of newly derived nodes

**Example:**
```python
engine = RuleEngine(store)

# Apply employment law rules
new_facts = engine.apply_rules(employment_rules, context)
```

##### `get_reasoning_chain(conclusion_id: str) -> List[Dict[str, Any]]`

Gets the reasoning chain that led to a conclusion.

**Returns:** List of reasoning steps with rules and premises

### ConflictResolver

Resolves conflicts between competing legal conclusions.

```python
from core.reasoning import ConflictResolver

class ConflictResolver:
    def __init__(self, strategies: List[str] = None)
```

#### Methods

##### `resolve_conflicts(conclusions: List[Node]) -> List[Node]`

Resolves conflicts using configured strategies.

**Strategies:**
- `authority`: Higher legal authority wins
- `specificity`: More specific rules override general ones
- `temporal`: Newer rules override older ones

### Explanation Functions

##### `explain(conclusion: Node, reasoning_chain: List[Dict]) -> str`

Generates human-readable explanation for a legal conclusion.

**Example:**
```python
from core.reasoning import explain

explanation = explain(conclusion_node, reasoning_chain)
print(explanation)
# Output: "Based on 42 U.S.C. § 12112(b)(5)(A), when an employee has a disability 
#         and can perform essential job functions with accommodation, 
#         reasonable accommodation is required."
```

## Plugin SDK

### Base Interfaces

#### OntologyProvider

Abstract base class for domain ontology providers.

```python
from sdk.plugin import OntologyProvider

class OntologyProvider(ABC):
    @abstractmethod
    def get_ontology(self) -> Dict[str, Any]:
        """Return domain-specific ontology definition"""
        pass
```

#### RuleProvider

Abstract base class for legal rule providers.

```python
class RuleProvider(ABC):
    @abstractmethod
    def get_rules(self, context: Context) -> List[LegalRule]:
        """Return applicable legal rules for context"""
        pass
```

#### LegalExplainer

Abstract base class for explanation generators.

```python
class LegalExplainer(ABC):
    @abstractmethod
    def explain_conclusion(self, conclusion: Dict[str, Any], 
                         reasoning_chain: List[Dict]) -> str:
        """Generate human-readable explanation"""
        pass
```

### RawDoc

Data model for input documents.

```python
class RawDoc(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
```

## NLP Pipeline

### LegalNERPipeline

Named Entity Recognition for legal documents.

```python
from nlp.legal_ner import LegalNERPipeline

class LegalNERPipeline:
    def __init__(self, model_name: str = "nlpaueb/legal-bert-base-uncased")
```

#### Methods

##### `extract_legal_entities(text: str) -> List[Dict[str, Any]]`

Extracts legal entities from text.

**Returns:** List of entities with text, label, start, end, confidence

##### `extract_obligations(text: str) -> List[Dict[str, Any]]`

Extracts legal obligations and requirements.

##### `extract_pattern_entities(text: str, patterns: Dict[str, str]) -> List[Dict]`

Extracts entities using custom regex patterns.

**Example:**
```python
ner = LegalNERPipeline()

entities = ner.extract_legal_entities(
    "Employee requests reasonable accommodation under ADA."
)
# Returns: [{'text': 'reasonable accommodation', 'label': 'LEGAL_CONCEPT', ...}]
```

### CitationExtractor

Extracts and normalizes legal citations.

```python
from nlp.legal_ner import CitationExtractor

class CitationExtractor:
    def __init__(self)
```

#### Methods

##### `extract_citations(text: str) -> List[Dict[str, Any]]`

Extracts all types of legal citations.

##### `extract_case_citations(text: str) -> List[Dict[str, Any]]`

Extracts case law citations.

##### `extract_statute_citations(text: str) -> List[Dict[str, Any]]`

Extracts statutory citations.

##### `normalize_citation(citation: str) -> str`

Normalizes citation format.

**Example:**
```python
extractor = CitationExtractor()

citations = extractor.extract_citations(
    "See 42 U.S.C. § 12112 and Brown v. Board, 347 U.S. 483 (1954)."
)
```

## CLI Interface

### LegalAnalysisCLI

Main CLI interface class.

```python
from cli_driver import LegalAnalysisCLI

class LegalAnalysisCLI:
    def __init__(self)
```

#### Methods

##### `analyze_document(file_path: str, output_format: str = "summary", jurisdiction: str = "US", show_reasoning: bool = False) -> Dict[str, Any]`

Analyzes a single legal document.

**Parameters:**
- `file_path`: Path to document file
- `output_format`: "summary", "detailed", or "json"
- `jurisdiction`: Legal jurisdiction
- `show_reasoning`: Include reasoning steps

**Returns:** Analysis results dictionary

##### `run_demo() -> None`

Runs interactive demo mode.

##### `batch_analyze(directory: str, output_format: str = "summary", output_file: Optional[str] = None) -> None`

Analyzes multiple documents in a directory.

### Command Line Usage

```bash
# Basic analysis
python cli_driver.py analyze --file document.txt

# Detailed output
python cli_driver.py analyze --file document.txt --format detailed

# JSON output
python cli_driver.py analyze --file document.txt --format json

# Interactive demo
python cli_driver.py demo

# Batch processing
python cli_driver.py batch --directory docs/
```

## Employment Law Plugin

### EmploymentLawPlugin

Main plugin class implementing all interfaces.

```python
from plugins.employment_law.plugin import EmploymentLawPlugin

class EmploymentLawPlugin(OntologyProvider, RuleProvider, LegalExplainer):
    def __init__(self)
```

#### Methods

##### `analyze_document(content: str, context: Context = None) -> Dict[str, Any]`

Performs complete employment law analysis.

**Returns:** Dictionary with entities, facts, conclusions, and explanations

##### `get_ontology() -> Dict[str, Any]`

Returns employment law ontology.

##### `get_rules(context: Context) -> List[LegalRule]`

Returns applicable employment law rules.

##### `explain_conclusion(conclusion: Dict, reasoning_chain: List) -> str`

Generates employment-specific explanations.

### EmploymentNER

Employment law specific entity recognition.

```python
from plugins.employment_law.ner import EmploymentNER

class EmploymentNER:
    def __init__(self)
```

#### Entity Types

- **ADA_REQUEST**: Accommodation requests and ADA references
- **DISABILITY**: Disability types and conditions  
- **REASONABLE_ACCOMMODATION**: Specific accommodations
- **INTERACTIVE_PROCESS**: ADA interactive process references
- **FLSA_VIOLATION**: FLSA violations and overtime issues
- **OVERTIME**: Overtime work and pay references
- **WAGE_RATE**: Hourly rates and wage information
- **AT_WILL_EMPLOYMENT**: At-will employment references
- **WRONGFUL_TERMINATION**: Wrongful termination claims
- **WHISTLEBLOWING**: Whistleblower protections
- **PUBLIC_POLICY_EXCEPTION**: Public policy exceptions
- **RETALIATION**: Employer retaliation
- **WORKERS_COMP_CLAIM**: Workers' compensation claims
- **MEDICAL_TREATMENT**: Medical treatment for injuries
- **LOST_WAGES**: Lost wage claims

#### Methods

##### `extract_entities(text: str) -> List[Dict[str, Any]]`

Extracts employment law entities from text.

### EmploymentLawRules

Employment law rule definitions.

```python
from plugins.employment_law.rules import EmploymentLawRules

class EmploymentLawRules:
    def get_all_rules(self) -> List[LegalRule]
```

#### Rule Categories

**ADA Rules (4 rules):**
- Reasonable accommodation requirements
- Undue hardship analysis
- Interactive process obligations
- Essential function determination

**FLSA Rules (4 rules):**
- 40-hour workweek standards
- Overtime calculation requirements
- Minimum wage compliance
- Recordkeeping obligations

**At-Will Employment Rules (3 rules):**
- Public policy exceptions
- Implied contract exceptions
- Wrongful termination standards

**Workers' Compensation Rules (3 rules):**
- Injury compensability
- Medical treatment coverage
- Lost wage calculations

**Other Rules (2 rules):**
- Retaliation prohibitions
- General employment protections

## Error Handling

### Custom Exceptions

```python
# Plugin loading errors
class PluginLoadError(Exception):
    pass

# Validation errors  
class ValidationError(Exception):
    pass

# Analysis errors
class AnalysisError(Exception):
    pass
```

### Error Response Format

```json
{
  "error": true,
  "error_type": "AnalysisError",
  "message": "Document analysis failed",
  "details": {
    "file_path": "document.txt",
    "timestamp": "2024-03-15T10:30:00Z"
  }
}
```

## Configuration

### Environment Variables

```bash
# Enable debug logging
export LEGAL_ANALYSIS_DEBUG=1

# Set custom model path
export LEGAL_BERT_MODEL_PATH=/path/to/model

# Database configuration
export LEGAL_DB_PATH=/path/to/database
```

### Configuration Files

The system supports configuration through `config.json`:

```json
{
  "storage": {
    "path": "legal_graph.db",
    "auto_backup": true
  },
  "nlp": {
    "model_name": "nlpaueb/legal-bert-base-uncased",
    "confidence_threshold": 0.7
  },
  "reasoning": {
    "max_iterations": 100,
    "conflict_resolution": ["authority", "specificity", "temporal"]
  },
  "plugins": {
    "enabled": ["employment_law"],
    "auto_load": true
  }
}
```

---

This API documentation provides comprehensive coverage of all system components. For implementation examples, see [EXAMPLES.md](EXAMPLES.md).