# API Documentation

Complete API reference for the OpenLaw Legal Hypergraph System.

## Table of Contents

- [CLI API](#cli-api)
- [Python API](#python-api)
- [Core Classes](#core-classes)
- [Plugin API](#plugin-api)
- [Data Models](#data-models)
- [Response Formats](#response-formats)
- [Error Handling](#error-handling)
- [Examples](#examples)

Implementation note: Native Legal Engine is the default implementation; the adapter is [NativeLegalBridge](core/adapters/native_bridge.py:1). Use [doc_to_graph_cli.py](scripts/ingest/doc_to_graph_cli.py:1) to build GraphML graphs for native ingestion when starting from raw text.
## CLI API

### Command Line Interface

The primary interface for document analysis and system interaction.

#### `analyze` Command

Analyze a single legal document.

```bash
python3 cli_driver.py analyze [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--file, -f` | string | Yes | Path to document file |
| `--format` | choice | No | Output format: `summary`, `detailed`, `json` |
| `--jurisdiction, -j` | string | No | Legal jurisdiction (default: `US`) |
| `--show-reasoning` | flag | No | Show detailed reasoning steps |

**Examples:**

```bash
# Basic analysis
python3 cli_driver.py analyze --file document.txt

# Detailed analysis with reasoning
python3 cli_driver.py analyze --file document.txt --format detailed --show-reasoning

# JSON output for integration
python3 cli_driver.py analyze --file document.txt --format json
```

**Response Formats:**

- **Summary**: Brief overview with key findings
- **Detailed**: Complete analysis with entity details
- **JSON**: Machine-readable structured output

#### `demo` Command

Run interactive demonstration.

```bash
python3 cli_driver.py demo [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--domain` | choice | No | Legal domain: `employment_law` (default) |

**Example:**

```bash
python3 cli_driver.py demo --domain employment_law
```

#### `batch` Command

Process multiple documents.

```bash
python3 cli_driver.py batch [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--directory, -d` | string | Yes | Directory containing documents |
| `--format` | choice | No | Output format: `summary`, `detailed`, `json` |
| `--output, -o` | string | No | Save results to file (JSON format) |

**Example:**

```bash
python3 cli_driver.py batch --directory documents/ --output results.json
```

## Python API

### Core Imports

```python
# Core system components
from core.model import Context, Node, Hyperedge, mk_node, mk_edge, Provenance
from core.storage import GraphStore
from core.reasoning import RuleEngine, explain
from core.rules import LegalRule

# Plugin system
from plugins.employment_law.plugin import EmploymentLawPlugin
```

### Quick Start Example

```python
from plugins.employment_law.plugin import EmploymentLawPlugin
from core.model import Context

# Initialize plugin
plugin = EmploymentLawPlugin()

# Create analysis context
context = Context(jurisdiction="US", law_type="employment")

# Analyze document
document_text = """
Employee has a visual impairment and requested 
screen reader software as accommodation.
"""

results = plugin.analyze_document(document_text, context)

# Access results
entities = results['entities']
conclusions = results['conclusions']
reasoning = results['derived_facts']
```

## Core Classes

### Context

Legal analysis context and configuration.

```python
class Context:
    """Legal analysis context"""
    
    def __init__(self, jurisdiction: str = "US", law_type: str = "general"):
        self.jurisdiction = jurisdiction
        self.law_type = law_type
        self.metadata = {}
```

**Parameters:**

- `jurisdiction` (str): Legal jurisdiction (e.g., "US", "CA", "UK")
- `law_type` (str): Type of law (e.g., "employment", "contract", "tort")
- `metadata` (dict): Additional context metadata

### Node

Graph node representing legal facts or entities.

```python
class Node:
    """Hypergraph node"""
    
    def __init__(self, id: str, type: str, data: Dict[str, Any], prov: Provenance):
        self.id = id
        self.type = type
        self.data = data
        self.prov = prov
```

**Attributes:**

- `id` (str): Unique node identifier
- `type` (str): Node type (e.g., "Fact", "Entity", "Rule")
- `data` (dict): Node data payload
- `prov` (Provenance): Provenance tracking information

### Hyperedge

Graph edge representing relationships between nodes.

```python
class Hyperedge:
    """Hypergraph edge connecting multiple nodes"""
    
    def __init__(self, id: str, type: str, nodes: List[str], data: Dict[str, Any], prov: Provenance):
        self.id = id
        self.type = type
        self.nodes = nodes
        self.data = data
        self.prov = prov
```

### Provenance

Audit trail for legal reasoning.

```python
class Provenance:
    """Provenance tracking for legal conclusions"""
    
    def __init__(self, source: List[Dict], method: str, agent: str, 
                 time: datetime, confidence: float):
        self.source = source
        self.method = method
        self.agent = agent
        self.time = time
        self.confidence = confidence
```

**Parameters:**

- `source` (List[Dict]): Source information and references
- `method` (str): Analysis method used
- `agent` (str): System component that generated result
- `time` (datetime): Timestamp of analysis
- `confidence` (float): Confidence score (0.0-1.0)

### GraphStore

Hypergraph storage and retrieval.

```python
class GraphStore:
    """Hypergraph storage interface"""
    
    def __init__(self, db_path: str):
        """Initialize graph store"""
        
    def add_node(self, node: Node) -> None:
        """Add node to graph"""
        
    def add_edge(self, edge: Hyperedge) -> None:
        """Add edge to graph"""
        
    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve node by ID"""
        
    def get_edges_for_node(self, node_id: str) -> List[Hyperedge]:
        """Get all edges connected to node"""
        
    def query_nodes(self, query: Dict[str, Any]) -> List[Node]:
        """Query nodes by criteria"""
```

### RuleEngine

Legal reasoning and inference engine.

```python
class RuleEngine:
    """Legal rule-based reasoning engine"""
    
    def __init__(self, graph: GraphStore, context: Context):
        self.graph = graph
        self.context = context
        
    def forward_chain(self) -> List[Node]:
        """Execute forward chaining inference"""
        
    def explain_conclusion(self, conclusion_id: str) -> Dict[str, Any]:
        """Generate explanation for conclusion"""
```

### LegalRule

Formalized legal rule representation.

```python
class LegalRule:
    """Legal rule for reasoning"""
    
    def __init__(self, id: str, name: str, description: str, 
                 conditions: List[str], conclusion: str, 
                 authority: str, jurisdiction: str, confidence: float):
        self.id = id
        self.name = name
        self.description = description
        self.conditions = conditions
        self.conclusion = conclusion
        self.authority = authority
        self.jurisdiction = jurisdiction
        self.confidence = confidence
        
    def to_hyperedge(self) -> Hyperedge:
        """Convert rule to hypergraph edge"""
```

## Plugin API

### Plugin Base Class

```python
class PluginBase:
    """Base class for legal domain plugins"""
    
    def __init__(self):
        self.name: str
        self.version: str
        self.description: str
        
    def analyze_document(self, text: str, context: Context) -> Dict[str, Any]:
        """Analyze document with domain-specific logic"""
        
    def load_rules(self, graph: GraphStore, context: Context) -> None:
        """Load domain rules into graph"""
        
    def get_supported_domains(self) -> List[str]:
        """Get list of supported legal domains"""
```

### Employment Law Plugin

```python
class EmploymentLawPlugin:
    """Employment law analysis plugin"""
    
    def analyze_document(self, text: str, context: Context) -> Dict[str, Any]:
        """
        Analyze employment law document
        
        Args:
            text: Document text to analyze
            context: Legal context for analysis
            
        Returns:
            Analysis results with entities, facts, and conclusions
        """
        
    def explain_conclusion(self, graph: GraphStore, conclusion_id: str) -> Dict[str, Any]:
        """
        Generate detailed explanation for legal conclusion
        
        Args:
            graph: Graph containing reasoning chain
            conclusion_id: ID of conclusion to explain
            
        Returns:
            Structured explanation with legal reasoning
        """
```

## Data Models

### Analysis Result

```python
{
    "entities": [
        {
            "type": "DISABILITY",
            "text": "visual impairment",
            "start": 25,
            "end": 40,
            "confidence": 0.85,
            "metadata": {"category": "ada"}
        }
    ],
    "citations": [
        {
            "text": "42 U.S.C. § 12112",
            "start": 150,
            "end": 167,
            "metadata": {
                "citation_type": "statute",
                "normalized": "42 U.S.C. § 12112"
            }
        }
    ],
    "original_facts": [
        {
            "statement": "employee_has_disability",
            "disability_details": "visual impairment",
            "entity_type": "DISABILITY"
        }
    ],
    "derived_facts": [
        {
            "statement": "reasonable_accommodation_required",
            "rule_authority": "42 U.S.C. § 12112(b)(5)(A)"
        }
    ],
    "conclusions": [
        {
            "type": "ADA_VIOLATION",
            "conclusion": "Employer may be required to provide reasonable accommodation",
            "legal_basis": "42 U.S.C. § 12112(b)(5)(A)",
            "confidence": 0.85,
            "fact_id": "fact_123"
        }
    ],
    "context": {
        "jurisdiction": "US",
        "law_type": "employment"
    }
}
```

### Entity

```python
{
    "type": "REASONABLE_ACCOMMODATION",
    "text": "screen reader software",
    "start": 75,
    "end": 95,
    "confidence": 0.85,
    "metadata": {
        "category": "ada",
        "subcategory": "assistive_technology"
    }
}
```

### Legal Citation

```python
{
    "text": "29 U.S.C. § 207(a)(1)",
    "start": 200,
    "end": 220,
    "metadata": {
        "citation_type": "statute",
        "normalized": "29 U.S.C. § 207(a)(1)",
        "law": "FLSA",
        "section": "overtime"
    }
}
```

### Legal Conclusion

```python
{
    "type": "FLSA_VIOLATION",
    "conclusion": "Employee entitled to overtime compensation",
    "legal_basis": "29 U.S.C. § 207(a)(1)",
    "confidence": 0.90,
    "fact_id": "fact_456",
    "supporting_evidence": [
        "worked_over_40_hours",
        "employee_non_exempt"
    ]
}
```

## Response Formats

### Summary Format

Human-readable overview of analysis results.

```
📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 4 total
   • DISABILITY: 1
   • REASONABLE_ACCOMMODATION: 1
   • ADA_REQUEST: 2

📚 Legal Citations: 1
   • 42 U.S.C. § 12112

⚖️  Legal Conclusions: 1
   • ADA_VIOLATION: Employer may be required to provide reasonable accommodation
     Legal Basis: 42 U.S.C. § 12112(b)(5)(A)
     Confidence: 85.0%
```

### Detailed Format

Comprehensive analysis with entity details and reasoning.

```
📋 DETAILED ANALYSIS REPORT
================================================================================
Document: employment_case.txt
Analysis Time: 2025-08-23 18:00:00 UTC

🏷️  ENTITY EXTRACTION RESULTS
--------------------------------------------------
Type: DISABILITY
Text: visual impairment
Confidence: 85.0%
Category: ada

🧠 REASONING PROCESS
--------------------------------------------------
Original Facts:
   • employee_has_disability
   • can_perform_essential_functions_with_accommodation

Derived Facts:
   • reasonable_accommodation_required
     Authority: 42 U.S.C. § 12112(b)(5)(A)
```

### JSON Format

Structured output for programmatic use.

```json
{
    "document_path": "employment_case.txt",
    "analysis_time": "2025-08-23T18:00:00Z",
    "analysis_results": {
        "entities": [...],
        "citations": [...],
        "conclusions": [...]
    }
}
```

## Error Handling

### Common Errors

#### FileNotFoundError

```python
try:
    results = plugin.analyze_document(text, context)
except FileNotFoundError as e:
    print(f"❌ File not found: {e}")
```

#### ImportError

```python
try:
    from plugins.contract_law.plugin import ContractLawPlugin
except ImportError as e:
    print(f"❌ Plugin not available: {e}")
```

#### ValidationError

```python
from pydantic import ValidationError

try:
    context = Context(jurisdiction="INVALID")
except ValidationError as e:
    print(f"❌ Invalid context: {e}")
```

### Error Response Format

```json
{
    "error": {
        "type": "AnalysisError",
        "message": "Unable to process document",
        "details": {
            "file": "document.txt",
            "line": 45,
            "cause": "Invalid character encoding"
        }
    }
}
```

## Examples

### Basic Document Analysis

```python
from plugins.employment_law.plugin import EmploymentLawPlugin
from core.model import Context

# Initialize components
plugin = EmploymentLawPlugin()
context = Context(jurisdiction="US", law_type="employment")

# Document text
text = """
Employee worked 50 hours per week for 6 months without 
receiving overtime pay. Company policy states all employees 
are exempt from overtime requirements.
"""

# Analyze document
results = plugin.analyze_document(text, context)

# Print results
print(f"Entities: {len(results['entities'])}")
print(f"Conclusions: {len(results['conclusions'])}")

for conclusion in results['conclusions']:
    print(f"- {conclusion['type']}: {conclusion['conclusion']}")
    print(f"  Legal Basis: {conclusion['legal_basis']}")
    print(f"  Confidence: {conclusion['confidence']:.1%}")
```

### Custom Rule Creation

```python
from core.rules import LegalRule

# Create custom rule
rule = LegalRule(
    id="custom_overtime_rule",
    name="Custom Overtime Rule",
    description="Employees working over 40 hours must receive overtime",
    conditions=["worked_over_40_hours", "employee_non_exempt"],
    conclusion="overtime_pay_required",
    authority="29 U.S.C. § 207(a)(1)",
    jurisdiction="US",
    confidence=0.95
)

# Add to graph
graph = GraphStore(":memory:")
graph.add_edge(rule.to_hyperedge())
```

### Explanation Generation

```python
# Get explanation for conclusion
explanation = plugin.explain_conclusion(graph, "conclusion_123")

print(f"Conclusion: {explanation['conclusion']}")
print(f"Legal Basis: {explanation['legal_basis']}")
print(f"Supporting Facts:")
for fact in explanation['supporting_facts']:
    print(f"  - {fact['statement']}")
```

### Batch Processing

```python
import os
from pathlib import Path

def analyze_directory(directory_path: str):
    """Analyze all text files in directory"""
    plugin = EmploymentLawPlugin()
    context = Context(jurisdiction="US", law_type="employment")
    
    results = []
    for file_path in Path(directory_path).glob("*.txt"):
        with open(file_path, 'r') as f:
            text = f.read()
        
        try:
            analysis = plugin.analyze_document(text, context)
            results.append({
                "file": str(file_path),
                "status": "success",
                "analysis": analysis
            })
        except Exception as e:
            results.append({
                "file": str(file_path),
                "status": "error",
                "error": str(e)
            })
    
    return results

# Usage
results = analyze_directory("./legal_documents/")
```

## Performance Considerations

### Memory Usage

- **Base System**: ~100MB
- **Per Document**: ~1MB for 10KB text
- **Plugin Loading**: ~10-50MB per plugin

### Processing Time

- **Small Documents** (<10KB): 1-2 seconds
- **Medium Documents** (10-100KB): 2-5 seconds  
- **Large Documents** (100KB-1MB): 5-15 seconds

### Optimization Tips

1. **Reuse Components**: Initialize plugins once, reuse for multiple documents
2. **Batch Processing**: Process multiple documents in single session
3. **Memory Management**: Use in-memory storage for temporary analysis
4. **Caching**: Cache rule loading and NER models

```python
# Efficient batch processing
plugin = EmploymentLawPlugin()  # Initialize once
context = Context(jurisdiction="US", law_type="employment")

for document in documents:
    results = plugin.analyze_document(document, context)
    # Process results...