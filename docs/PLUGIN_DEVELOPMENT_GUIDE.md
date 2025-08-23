# Plugin Development Guide

This guide provides comprehensive instructions for developing plugins for the OpenLaw Legal Hypergraph System.

## Table of Contents

- [Overview](#overview)
- [Plugin Architecture](#plugin-architecture)
- [Getting Started](#getting-started)
- [SDK Interfaces](#sdk-interfaces)
- [Implementation Examples](#implementation-examples)
- [Testing Plugins](#testing-plugins)
- [Best Practices](#best-practices)

## Overview

The OpenLaw plugin system allows you to extend the legal analysis capabilities to new domains. Each plugin provides:

- **Domain-specific NER**: Named Entity Recognition for legal concepts
- **Legal Rules**: Formalized rules for reasoning and inference
- **Document Analysis**: Complete document processing pipeline
- **Explainable Results**: Audit trails and reasoning explanations

## Plugin Architecture

### Core Components

```
plugins/
└── your_domain/
    ├── __init__.py           # Plugin registration
    ├── plugin.py             # Main plugin class
    ├── ner.py               # Named entity recognition
    ├── rules.py             # Legal rules and reasoning
    ├── tests/               # Plugin test suite
    │   ├── __init__.py
    │   ├── test_plugin.py
    │   ├── test_ner.py
    │   └── test_rules.py
    └── data/                # Training data, models
        ├── entities.json
        ├── rules.yaml
        └── examples/
```

### Plugin Lifecycle

1. **Registration**: Plugin discovered and loaded
2. **Initialization**: Components initialized and rules loaded
3. **Analysis**: Documents processed with domain-specific logic
4. **Results**: Structured output with provenance tracking

## Getting Started

### 1. Create Plugin Structure

```bash
# Create plugin directory
mkdir -p plugins/contract_law/{tests,data/examples}

# Create required files
touch plugins/contract_law/__init__.py
touch plugins/contract_law/plugin.py
touch plugins/contract_law/ner.py
touch plugins/contract_law/rules.py
```

### 2. Implement Main Plugin Class

```python
# plugins/contract_law/plugin.py
from typing import List, Dict, Any
from datetime import datetime

from core.model import Context, Node, mk_node, Provenance
from core.storage import GraphStore
from core.reasoning import RuleEngine
from .ner import ContractNER
from .rules import ContractRules

class ContractLawPlugin:
    """Contract Law Domain Plugin"""
    
    def __init__(self):
        self.name = "Contract Law"
        self.version = "1.0.0"
        self.description = "Contract analysis with formation, breach, and remedies"
        
        # Initialize components
        self.ner = ContractNER()
        self.rules = ContractRules()
    
    def analyze_document(self, text: str, context: Context) -> Dict[str, Any]:
        """Analyze contract document"""
        # Extract entities
        entities = self.ner.extract_entities(text)
        citations = self.ner.extract_legal_citations(text)
        
        # Create analysis graph
        graph = GraphStore(":memory:")
        self.load_rules(graph, context)
        
        # Convert entities to facts
        facts = self._entities_to_facts(entities, self._create_provenance(text))
        for fact in facts:
            graph.add_node(fact)
        
        # Run reasoning
        engine = RuleEngine(graph, context)
        derived_facts = engine.forward_chain()
        
        return {
            "entities": entities,
            "citations": citations,
            "original_facts": [f.data for f in facts],
            "derived_facts": [f.data for f in derived_facts],
            "conclusions": self._extract_conclusions(derived_facts),
            "context": context.model_dump() if context else None
        }
    
    def load_rules(self, graph: GraphStore, context: Context) -> None:
        """Load contract law rules into graph"""
        rules = self.rules.get_all_rules()
        for rule in rules:
            graph.add_edge(rule.to_hyperedge())
    
    def _create_provenance(self, text: str) -> Provenance:
        """Create provenance for document analysis"""
        return Provenance(
            source=[{
                "type": "document_analysis",
                "method": "contract_ner",
                "text_length": len(text)
            }],
            method="nlp.extraction",
            agent="contract.plugin",
            time=datetime.utcnow(),
            confidence=0.85
        )
    
    def _entities_to_facts(self, entities: List[Dict], prov: Provenance) -> List[Node]:
        """Convert NER entities to graph facts"""
        facts = []
        # Implementation specific to contract law
        return facts
    
    def _extract_conclusions(self, derived_facts: List[Node]) -> List[Dict[str, Any]]:
        """Extract legal conclusions from derived facts"""
        conclusions = []
        # Implementation specific to contract law
        return conclusions
```

### 3. Implement NER Component

```python
# plugins/contract_law/ner.py
import re
from typing import List, Dict, Any

class ContractNER:
    """Contract Law Named Entity Recognition"""
    
    def __init__(self):
        self.entity_patterns = {
            "OFFER": [
                r"offer(?:s|ed|ing)?\s+to\s+\w+",
                r"propose(?:s|d|ing)?\s+that",
                r"willing\s+to\s+\w+"
            ],
            "ACCEPTANCE": [
                r"accept(?:s|ed|ing)?\s+the\s+offer",
                r"agree(?:s|d|ing)?\s+to\s+the\s+terms",
                r"consent(?:s|ed|ing)?\s+to"
            ],
            "CONSIDERATION": [
                r"\$[\d,]+(?:\.\d{2})?",
                r"consideration\s+of",
                r"in\s+exchange\s+for",
                r"payment\s+of"
            ],
            "BREACH": [
                r"breach(?:ed|ing)?\s+(?:the\s+)?contract",
                r"fail(?:ed|ure)?\s+to\s+perform",
                r"violation\s+of\s+terms"
            ]
        }
        
        self.citation_patterns = [
            r"UCC\s+§?\s*\d+[-\d]*",
            r"Restatement.*Contracts.*§\s*\d+",
            r"\d+\s+\w+\s+\d+.*\(\w+.*\d{4}\)"
        ]
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract contract law entities from text"""
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "type": entity_type,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.85,
                        "metadata": {"category": "contract"}
                    })
        
        return entities
    
    def extract_legal_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from text"""
        citations = []
        
        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                citations.append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "metadata": {
                        "citation_type": "statute" if "UCC" in match.group() else "case",
                        "normalized": self._normalize_citation(match.group())
                    }
                })
        
        return citations
    
    def _normalize_citation(self, citation: str) -> str:
        """Normalize citation format"""
        # Implement citation normalization
        return citation.strip()
```

### 4. Implement Rules Component

```python
# plugins/contract_law/rules.py
from typing import List
from core.rules import LegalRule

class ContractRules:
    """Contract Law Legal Rules"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def get_all_rules(self) -> List[LegalRule]:
        """Get all contract law rules"""
        return self.rules
    
    def _load_rules(self) -> List[LegalRule]:
        """Load contract formation and breach rules"""
        rules = []
        
        # Contract formation rule
        rules.append(LegalRule(
            id="contract_formation",
            name="Valid Contract Formation",
            description="A valid contract requires offer, acceptance, and consideration",
            conditions=[
                "offer_present",
                "acceptance_present", 
                "consideration_present"
            ],
            conclusion="valid_contract_formed",
            authority="Restatement (Second) of Contracts § 17",
            jurisdiction="US",
            confidence=0.95
        ))
        
        # Breach of contract rule
        rules.append(LegalRule(
            id="material_breach",
            name="Material Breach of Contract",
            description="Material breach excuses performance by non-breaching party",
            conditions=[
                "valid_contract_formed",
                "material_breach_occurred"
            ],
            conclusion="non_breaching_party_excused",
            authority="Restatement (Second) of Contracts § 237",
            jurisdiction="US",
            confidence=0.90
        ))
        
        return rules
```

## SDK Interfaces

### OntologyProvider Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class OntologyProvider(ABC):
    """Interface for domain ontology providers"""
    
    @abstractmethod
    def get_entity_types(self) -> List[str]:
        """Return list of entity types supported by this domain"""
        pass
    
    @abstractmethod
    def get_relationship_types(self) -> List[str]:
        """Return list of relationship types"""
        pass
    
    @abstractmethod
    def validate_entity(self, entity: Dict[str, Any]) -> bool:
        """Validate entity against domain ontology"""
        pass
```

### RuleProvider Interface

```python
class RuleProvider(ABC):
    """Interface for legal rule providers"""
    
    @abstractmethod
    def get_rules(self, domain: str) -> List[LegalRule]:
        """Get rules for specified domain"""
        pass
    
    @abstractmethod
    def validate_rule(self, rule: LegalRule) -> bool:
        """Validate rule syntax and semantics"""
        pass
```

### LegalExplainer Interface

```python
class LegalExplainer(ABC):
    """Interface for generating legal explanations"""
    
    @abstractmethod
    def explain_conclusion(self, conclusion_id: str, graph: GraphStore) -> Dict[str, Any]:
        """Generate explanation for legal conclusion"""
        pass
    
    @abstractmethod
    def get_supporting_evidence(self, conclusion_id: str) -> List[Dict[str, Any]]:
        """Get evidence supporting conclusion"""
        pass
```

## Implementation Examples

### Employment Law Plugin (Reference)

See the employment law plugin for a complete implementation:

```python
# Key patterns from employment law plugin:

# 1. Entity-to-fact conversion
def _entities_to_facts(self, entities, prov):
    facts = []
    for entity in entities:
        if entity["type"] == "DISABILITY":
            fact = mk_node("Fact", {
                "statement": "employee_has_disability",
                "disability_details": entity["text"]
            }, prov)
            facts.append(fact)
    return facts

# 2. Conclusion extraction
def _extract_conclusions(self, derived_facts):
    conclusions = []
    for fact in derived_facts:
        if fact.data.get("statement") == "reasonable_accommodation_required":
            conclusions.append({
                "type": "ADA_VIOLATION",
                "conclusion": "Employer may be required to provide reasonable accommodation",
                "legal_basis": "42 U.S.C. § 12112(b)(5)(A)",
                "confidence": fact.prov.confidence
            })
    return conclusions
```

## Testing Plugins

### Test Structure

```python
# plugins/contract_law/tests/test_plugin.py
import pytest
from core.model import Context
from ..plugin import ContractLawPlugin

class TestContractLawPlugin:
    
    def setup_method(self):
        self.plugin = ContractLawPlugin()
        self.context = Context(jurisdiction="US", law_type="contract")
    
    def test_plugin_initialization(self):
        assert self.plugin.name == "Contract Law"
        assert self.plugin.version == "1.0.0"
        assert self.plugin.ner is not None
        assert self.plugin.rules is not None
    
    def test_analyze_contract_formation(self):
        text = """
        Company offers to sell 100 widgets for $1000.
        Buyer accepts the offer and agrees to pay $1000.
        Payment of $1000 constitutes consideration.
        """
        
        results = self.plugin.analyze_document(text, self.context)
        
        assert len(results["entities"]) > 0
        assert any(e["type"] == "OFFER" for e in results["entities"])
        assert any(e["type"] == "ACCEPTANCE" for e in results["entities"]) 
        assert any(e["type"] == "CONSIDERATION" for e in results["entities"])
        
        # Check for contract formation conclusion
        conclusions = results["conclusions"]
        assert any(c.get("type") == "CONTRACT_FORMATION" for c in conclusions)
```

### Running Tests

```bash
# Test specific plugin
pytest plugins/contract_law/tests/ -v

# Test with coverage
pytest plugins/contract_law/tests/ --cov=plugins.contract_law

# Integration tests
pytest tests/integration/test_contract_plugin.py
```

## Best Practices

### 1. Entity Design

- **Specific Types**: Create domain-specific entity types
- **Rich Metadata**: Include confidence scores and context
- **Normalization**: Standardize entity formats
- **Validation**: Implement entity validation

### 2. Rule Design

- **Atomic Rules**: Break complex logic into simple rules
- **Clear Conditions**: Use precise, testable conditions
- **Legal Authority**: Always cite legal sources
- **Confidence Scores**: Reflect rule certainty

### 3. Performance

- **Lazy Loading**: Load rules and models on demand
- **Caching**: Cache expensive computations
- **Batch Processing**: Optimize for multiple documents
- **Memory Management**: Clean up resources

### 4. Documentation

- **API Documentation**: Document all public methods
- **Examples**: Provide working code examples
- **Legal Context**: Explain legal concepts and terminology
- **Testing**: Comprehensive test coverage

### 5. Error Handling

- **Graceful Degradation**: Continue processing on errors
- **Detailed Logging**: Log errors with context
- **User Feedback**: Provide meaningful error messages
- **Recovery**: Implement retry mechanisms

## Plugin Registration

### Automatic Discovery

Plugins are automatically discovered in the `plugins/` directory. Ensure your plugin directory includes:

```python
# plugins/contract_law/__init__.py
from .plugin import ContractLawPlugin

__all__ = ["ContractLawPlugin"]
```

### Manual Registration

For advanced scenarios, register plugins manually:

```python
from core.plugin_manager import PluginManager
from plugins.contract_law.plugin import ContractLawPlugin

manager = PluginManager()
manager.register_plugin("contract_law", ContractLawPlugin())
```

## Advanced Features

### Custom Storage Backends

```python
class ContractStorageAdapter:
    """Custom storage for contract-specific data"""
    
    def store_contract(self, contract_data):
        # Implementation for contract storage
        pass
    
    def retrieve_contracts(self, query):
        # Implementation for contract retrieval
        pass
```

### Machine Learning Integration

```python
from transformers import AutoTokenizer, AutoModel

class ContractMLClassifier:
    """ML-based contract classification"""
    
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("legal-bert")
        self.model = AutoModel.from_pretrained("legal-bert")
    
    def classify_contract_type(self, text):
        # Implementation for ML classification
        pass
```

## Getting Help

- **Documentation**: [`docs/`](../README.md)
- **Examples**: [`plugins/employment_law/`](../../plugins/employment_law/)
- **Issues**: [GitHub Issues](../../issues)
- **Community**: Legal AI development community

## Next Steps

1. **Review Examples**: Study the employment law plugin implementation
2. **Create Plugin**: Follow the getting started guide
3. **Test Thoroughly**: Implement comprehensive tests
4. **Document**: Create clear documentation and examples
5. **Contribute**: Submit plugins to the community repository