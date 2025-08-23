# CAP Caselaw Plugin - Data Models & Schemas

## Overview

This document specifies the complete data models and schemas for the CAP caselaw plugin, implementing a provenance-first hypergraph with canonical identifiers.

## 🔑 Canonical Identifier System

### ID Generation Functions

```python
class CaselawIdentifiers:
    """Canonical ID generators following specification"""
    
    @staticmethod
    def doc_id(cap_id: int) -> str:
        """Generate stable case ID: cap:{numeric_id}"""
        return f"cap:{cap_id}"
    
    @staticmethod
    def para_id(cap_id: int, paragraph_num: int) -> str:
        """Generate paragraph anchor: cap:{case_id}#¶{n}"""
        return f"cap:{cap_id}#¶{paragraph_num}"
    
    @staticmethod
    def cite_id(citation_data: Dict[str, Any]) -> str:
        """Generate canonical citation ID: reporter:vol:page or cl:{id}"""
        if all(k in citation_data for k in ["reporter", "volume", "page"]):
            return f"{citation_data['reporter']}:{citation_data['volume']}:{citation_data['page']}"
        elif "courtlistener_id" in citation_data:
            return f"cl:{citation_data['courtlistener_id']}"
        else:
            return f"cite:{hash(citation_data.get('normalized_text', ''))}"
    
    @staticmethod
    def statute_id(title: str, section: str) -> str:
        """Generate statute ID: usc:17:107"""
        return f"usc:{title}:{section}"
    
    @staticmethod
    def transform_id(config: Dict[str, Any], code_hash: str) -> str:
        """Generate deterministic transform ID"""
        config_hash = hash(json.dumps(config, sort_keys=True))
        return f"tr:{hashlib.sha256(f'{config_hash}_{code_hash}'.encode()).hexdigest()[:12]}"
    
    @staticmethod
    def artifact_id(kind: str, content_hash: str) -> str:
        """Generate artifact ID: artifact:{kind}:{hash}"""
        return f"artifact:{kind}:{content_hash[:12]}"
```

## 📊 Core Data Models

### Provenance Model

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Provenance(BaseModel):
    """Core provenance model - enforced on all entities"""
    # Required fields (non-negotiable)
    source: List[Dict[str, Any]] = Field(..., min_items=1)  # Citations with pinpoint
    method: str = Field(..., min_length=1)                  # plugin.module.function/version
    agent: str = Field(..., min_length=1)                   # plugin id@version or user
    time: datetime                                           # UTC creation time
    confidence: float = Field(..., ge=0.0, le=1.0)         # Confidence score
    
    # Optional enrichment
    hash: Optional[str] = None                               # Content hash for integrity
    evidence: Optional[Dict[str, Any]] = None               # NLP features, spans, etc.
    derivation: Optional[List[str]] = None                   # Supporting edge IDs for derived facts
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
```

### Context Model

```python
class Context(BaseModel):
    """Legal context for jurisdiction and temporal validity"""
    jurisdiction: Optional[str] = None                       # "US", "US-CA", "US-CA-SF"
    valid_from: Optional[datetime] = None                    # Temporal validity window
    valid_to: Optional[datetime] = None
    law_type: Optional[str] = None                          # "statute", "regulation", "case-law"
    authority_level: Optional[str] = None                   # "federal", "state", "local"
    
    def is_applicable_in(self, other: 'Context') -> bool:
        """Check if this context applies within another context"""
        if self.jurisdiction and other.jurisdiction:
            if not other.jurisdiction.startswith(self.jurisdiction):
                return False
        
        if self.valid_from and other.valid_from:
            if other.valid_from < self.valid_from:
                return False
                
        if self.valid_to and other.valid_to:
            if other.valid_to > self.valid_to:
                return False
                
        return True
```

### Node Models

```python
class Node(BaseModel):
    """Hypergraph node with provenance"""
    id: str = Field(default_factory=lambda: f"node:{uuid.uuid4().hex[:12]}")
    type: str
    labels: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Context] = None
    prov: Provenance

class CaseNode(Node):
    """Case document node"""
    type: str = "Case"
    
    @property
    def doc_id(self) -> str:
        return self.data.get("doc_id", self.id)
    
    @property
    def title(self) -> str:
        return self.data.get("title", "")
    
    @property
    def decision_date(self) -> Optional[datetime]:
        date_str = self.data.get("decision_date")
        return datetime.fromisoformat(date_str) if date_str else None
    
    @property
    def court_info(self) -> Dict[str, Any]:
        return self.data.get("court", {})
    
    @property
    def jurisdiction_info(self) -> Dict[str, Any]:
        return self.data.get("jurisdiction", {})

class ParagraphNode(Node):
    """Case paragraph node"""
    type: str = "Paragraph"
    
    @property
    def para_id(self) -> str:
        return self.data.get("para_id", self.id)
    
    @property
    def text(self) -> str:
        return self.data.get("text", "")
    
    @property
    def byte_offsets(self) -> Dict[str, int]:
        return self.data.get("offsets", {"start": 0, "end": 0})

class CitationNode(Node):
    """Citation node"""
    type: str = "Citation"
    
    @property
    def cite_id(self) -> str:
        return self.data.get("cite_id", self.id)
    
    @property
    def normalized_text(self) -> str:
        return self.data.get("normalized_text", "")
    
    @property
    def citation_type(self) -> str:
        return self.data.get("citation_type", "case")
```

### Hyperedge Models

```python
class Hyperedge(BaseModel):
    """Hypergraph edge supporting many-to-many relationships"""
    id: str = Field(default_factory=lambda: f"edge:{uuid.uuid4().hex[:12]}")
    relation: str
    tails: List[str] = Field(..., min_items=1)             # Input nodes (sources)
    heads: List[str] = Field(..., min_items=1)             # Output nodes (targets)
    qualifiers: Dict[str, Any] = Field(default_factory=dict) # Edge metadata
    context: Optional[Context] = None
    prov: Provenance
    
    def is_applicable_in(self, ctx: Optional[Context]) -> bool:
        """Check if this edge applies in the given context"""
        if not self.context or not ctx:
            return True
        return self.context.is_applicable_in(ctx)
```

## 🔗 Relationship Types

### Core Caselaw Relations

```python
class CaselawRelations:
    """Standard hyperedge relations for caselaw reasoning"""
    
    # Document structure
    HAS_OPINION = "has_opinion"           # Case → Opinion
    HAS_PARAGRAPH = "has_paragraph"       # Opinion → Paragraph
    AUTHORED_BY = "authored_by"           # Opinion → Judge
    DECIDED_IN = "decided_in"             # Case → Court → Jurisdiction
    
    # Citations and precedents
    CITES_CASE = "cites_case"             # Paragraph → Case (with evidence span)
    CITES_STATUTE = "cites_statute"       # Paragraph → Statute
    RESOLVES_CITATION = "resolves_citation" # Citation → Case (with confidence)
    
    # Legal relationships
    OVERRULES = "overrules"               # Case → Case
    DISTINGUISHES = "distinguishes"       # Case → Case
    FOLLOWS = "follows"                   # Case → Case
    ESTABLISHES_PRECEDENT = "establishes_precedent"  # Case → Rule
    
    # Provenance and derivation
    DERIVES_LABEL = "derives_label"       # Transform → Entity → Label
    DERIVES_ARTIFACT = "derives_artifact" # Transform → Entity → Artifact
    WAS_DERIVED_FROM = "was_derived_from" # Artifact/Label → Source
```

## 📋 Schema Examples

### Case Node Schema

```json
{
  "id": "cap:12345",
  "type": "Case",
  "labels": ["supreme_court", "constitutional_law"],
  "data": {
    "doc_id": "cap:12345",
    "title": "Brown v. Board of Education",
    "decision_date": "1954-05-17",
    "court": {
      "id": "scotus",
      "name": "Supreme Court of the United States",
      "jurisdiction": "US"
    },
    "jurisdiction": {
      "code": "US",
      "name": "United States"
    },
    "docket_number": "1",
    "citations": [
      {"reporter": "U.S.", "volume": "347", "page": "483"}
    ],
    "analysis_metrics": {
      "word_count": 5342,
      "paragraph_count": 23,
      "citation_count": 15
    },
    "hashes": {
      "sha256": "abc123def456..."
    }
  },
  "context": {
    "jurisdiction": "US",
    "law_type": "case_law",
    "authority_level": "federal"
  },
  "prov": {
    "source": [
      {
        "type": "HF:common-pile/caselaw_access_project",
        "cap_id": 12345,
        "source_sha256": "abc123def456..."
      }
    ],
    "method": "ingestion.hf_loader",
    "agent": "caselaw.plugin@1.0.0",
    "time": "2025-08-23T15:30:00Z",
    "confidence": 1.0
  }
}
```

### Paragraph Node Schema

```json
{
  "id": "cap:12345#¶17",
  "type": "Paragraph",
  "labels": ["holding", "constitutional_analysis"],
  "data": {
    "para_id": "cap:12345#¶17",
    "doc_id": "cap:12345",
    "idx": 17,
    "text": "We conclude that in the field of public education the doctrine of 'separate but equal' has no place.",
    "offsets": {
      "start": 3821,
      "end": 3974
    }
  },
  "prov": {
    "source": [
      {
        "type": "document_paragraph",
        "doc_id": "cap:12345",
        "paragraph_index": 17
      }
    ],
    "method": "extraction.paragraph_segmentation",
    "agent": "caselaw.plugin@1.0.0",
    "time": "2025-08-23T15:30:00Z",
    "confidence": 1.0
  }
}
```

### Citation Hyperedge Schema

```json
{
  "id": "edge:cite_abc123",
  "relation": "cites_case",
  "tails": ["cap:12345#¶17"],
  "heads": ["cap:67890"],
  "qualifiers": {
    "citation_id": "U.S.:347:483",
    "evidence_span": {
      "start": 13,
      "end": 42,
      "text": "Brown v. Board, 347 U.S. 483",
      "context": "...as established in Brown v. Board, 347 U.S. 483 (1954), separate educational..."
    },
    "resolution_method": "exact_match",
    "confidence": 0.98
  },
  "context": {
    "jurisdiction": "US",
    "law_type": "case_law"
  },
  "prov": {
    "source": [
      {
        "type": "citation_extraction",
        "source_doc_id": "cap:12345",
        "source_para_id": "cap:12345#¶17"
      }
    ],
    "method": "citation.pattern_extraction",
    "agent": "caselaw.citation_extractor@1.0.0",
    "time": "2025-08-23T15:30:00Z",
    "confidence": 0.98,
    "evidence": {
      "extraction_pattern": "case_citation_bluebook",
      "resolution_score": 0.98
    }
  }
}
```

## 🔄 Bitemporal Schema

### Versioning Strategy

All entities support bitemporal versioning:

- **Valid Time**: When the legal fact was true in the real world
- **Transaction Time**: When the fact was recorded in the system

```python
class BitemporalEntity(BaseModel):
    """Base model for bitemporal entities"""
    valid_time_start: Optional[datetime] = None    # When fact became valid
    valid_time_end: Optional[datetime] = None      # When fact became invalid
    transaction_time: datetime                      # When recorded in system
    version: int = 1                               # Version number
    supersedes: Optional[str] = None               # ID of superseded entity
```

### Entity Lifecycle

```python
# Example: Case overruling another case
original_precedent = {
    "id": "cap:12345",
    "valid_time_start": "1954-05-17",
    "valid_time_end": None,  # Still valid until overruled
    "transaction_time": "2025-08-23T15:30:00Z",
    "version": 1
}

# Later case overrules the precedent
overruled_precedent = {
    "id": "cap:12345", 
    "valid_time_start": "1954-05-17",
    "valid_time_end": "2020-06-15",  # Overruled on this date
    "transaction_time": "2025-08-23T16:00:00Z",
    "version": 2,
    "supersedes": "cap:12345:v1"
}
```

## 🏷️ Entity Type Hierarchy

```yaml
Node Types:
  Document:
    - Case
    - Statute  
    - Regulation
    - Brief
  
  Text:
    - Paragraph
    - Sentence
    - Span
  
  Legal:
    - Opinion
    - Holding
    - Issue
    - Rule
    - Precedent
  
  Citation:
    - CaseCitation
    - StatuteCitation
    - RegulationCitation
  
  Entity:
    - Judge
    - Court
    - Jurisdiction
    - Party
    - Attorney
  
  Process:
    - Transform
    - Artifact
    - Label

Relation Types:
  Structural:
    - has_opinion
    - has_paragraph
    - contains
  
  Citation:
    - cites_case
    - cites_statute
    - resolves_citation
  
  Legal:
    - overrules
    - distinguishes
    - follows
    - establishes_precedent
  
  Authority:
    - authored_by
    - decided_in
    - binding_on
  
  Provenance:
    - derives_label
    - derives_artifact
    - was_derived_from
```

## 🔍 Query Patterns

### Common Query Examples

```python
# Find all cases that cite a specific case
citing_cases = store.query(
    relation="cites_case",
    heads=["cap:12345"]  # Brown v. Board
)

# Find precedents established by Supreme Court
scotus_precedents = store.query(
    relation="establishes_precedent",
    tails_filter={"court.id": "scotus"}
)

# Find all overruling relationships in a jurisdiction
overruling_edges = store.query(
    relation="overrules",
    context_filter={"jurisdiction": "US-CA"}
)

# Trace provenance chain for a derived conclusion
provenance_chain = store.trace_provenance(
    entity_id="conclusion_123",
    max_depth=5
)
```

This data model provides the foundation for a fully provenance-tracked hypergraph that can answer "why" and "from where" questions with complete audit trails back to source documents and reasoning steps.