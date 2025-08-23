# CAP Caselaw Plugin - API Documentation

## Overview

This document provides comprehensive API documentation for the CAP caselaw plugin, focusing on the provenance query APIs that enable downstream legal AI to query for "why" and "from where" answers.

## 🔗 Base API Structure

### Authentication
All APIs require authentication via API key or JWT token.

```http
Authorization: Bearer <token>
Content-Type: application/json
```

### Response Format
All responses follow a standard format:

```json
{
  "success": true,
  "data": {...},
  "metadata": {
    "timestamp": "2025-08-23T15:30:00Z",
    "request_id": "req_123abc",
    "processing_time_ms": 245,
    "plugin_version": "1.0.0"
  },
  "provenance": {
    "query_method": "api.endpoint",
    "data_sources": ["cap_dataset", "citation_index"],
    "confidence": 0.95
  }
}
```

### Error Format
```json
{
  "success": false,
  "error": {
    "code": "CITATION_NOT_FOUND",
    "message": "Citation could not be resolved to a case",
    "details": {...}
  },
  "metadata": {...}
}
```

## 🔍 Provenance Query API

### Trace Provenance

Get complete provenance chain for any entity.

```http
GET /api/v1/provenance/trace/{entity_id}
```

**Parameters:**
- `entity_id` (path): ID of node/edge to trace
- `max_depth` (query): Maximum depth to traverse (default: 5)
- `include_evidence` (query): Include evidence spans (default: true)

**Example Request:**
```bash
curl -X GET "https://api.openlaw.com/cap/v1/provenance/trace/cap:12345#¶17?max_depth=3" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "target_id": "cap:12345#¶17",
    "trace_depth": 2,
    "source_documents": [
      {
        "doc_id": "cap:12345",
        "title": "Brown v. Board of Education",
        "citation": "347 U.S. 483 (1954)",
        "paragraph_index": 17,
        "byte_offsets": {"start": 3821, "end": 3974}
      }
    ],
    "transform_chain": [
      {
        "transform_id": "tr:extract_para",
        "method": "extraction.paragraph_segmentation",
        "agent": "caselaw.plugin@1.0.0",
        "timestamp": "2025-08-23T15:30:00Z",
        "confidence": 1.0
      }
    ],
    "evidence_spans": [
      {
        "text": "We conclude that in the field of public education...",
        "start": 0,
        "end": 95,
        "context": "constitutional analysis"
      }
    ]
  }
}
```

### Explain Retrieval Result

Explain why a specific result was returned for a query.

```http
POST /api/v1/provenance/explain/retrieval
```

**Request Body:**
```json
{
  "result_id": "cap:12345#¶17",
  "query_context": {
    "query": "separate but equal doctrine",
    "jurisdiction": "US",
    "search_type": "semantic"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "result_id": "cap:12345#¶17",
    "entity_type": "Paragraph",
    "retrieval_reasoning": [
      {
        "factor": "semantic_similarity",
        "score": 0.94,
        "explanation": "High semantic similarity to query terms"
      },
      {
        "factor": "authority_weight",
        "score": 1.0,
        "explanation": "Supreme Court precedent carries maximum authority"
      },
      {
        "factor": "jurisdictional_relevance",
        "score": 1.0,
        "explanation": "Federal precedent applies to US jurisdiction"
      }
    ],
    "source_evidence": [
      {
        "evidence_type": "textual_match",
        "spans": [
          {
            "text": "separate but equal",
            "start": 45,
            "end": 63,
            "match_score": 1.0
          }
        ]
      }
    ],
    "authority_chain": [
      {
        "level": "supreme_court",
        "court": "Supreme Court of the United States",
        "binding_strength": 1.0
      }
    ]
  }
}
```

### Explain Legal Conclusion

Explain how a legal conclusion was derived with full citation support.

```http
GET /api/v1/provenance/explain/conclusion/{conclusion_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "conclusion_id": "conclusion_123",
    "conclusion_statement": "Separate educational facilities are inherently unequal",
    "legal_reasoning": [
      {
        "step_type": "precedent_application",
        "premises": ["equal_protection_clause", "educational_context"],
        "rule_applied": "constitutional_equal_protection",
        "conclusion": "separate_inherently_unequal",
        "authority": "U.S. Const. Amend. XIV"
      }
    ],
    "precedent_chain": [
      {
        "case_id": "cap:12345",
        "citation": "Brown v. Board, 347 U.S. 483 (1954)",
        "holding": "Separate educational facilities are inherently unequal",
        "precedential_weight": 1.0,
        "binding": true
      }
    ],
    "statutory_support": [
      {
        "statute_id": "const:us:amend:14",
        "citation": "U.S. Const. Amend. XIV",
        "relevant_text": "No State shall...deny to any person within its jurisdiction the equal protection of the laws",
        "authority_weight": 1.0
      }
    ]
  }
}
```

## 📚 Query & Search API

### Retrieve with Provenance

Main retrieval endpoint with full provenance tracking.

```http
POST /api/v1/search/retrieve
```

**Request Body:**
```json
{
  "query": "employment discrimination hostile environment",
  "jurisdiction": "US",
  "k": 10,
  "include_reasoning": true,
  "filters": {
    "date_range": {
      "start": "2000-01-01",
      "end": "2024-12-31"
    },
    "court_types": ["supreme_court", "circuit_court"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "employment discrimination hostile environment",
    "jurisdiction": "US",
    "results": [
      {
        "id": "cap:67890#¶5",
        "type": "Paragraph", 
        "text": "A workplace permeated with discriminatory intimidation...",
        "relevance_score": 0.92,
        "confidence": 0.88,
        "provenance_trace": {
          "source_case": {
            "id": "cap:67890",
            "citation": "Harris v. Forklift Systems, 510 U.S. 17 (1993)",
            "court": "Supreme Court of the United States"
          },
          "extraction_method": "paragraph_segmentation",
          "timestamp": "2025-08-23T15:30:00Z"
        },
        "explanation": {
          "retrieval_factors": [
            {
              "factor": "term_match",
              "score": 0.85,
              "matched_terms": ["discrimination", "hostile", "environment"]
            },
            {
              "factor": "legal_concept_match", 
              "score": 0.95,
              "concept": "hostile_work_environment"
            }
          ]
        },
        "source_citations": [
          {
            "citation": "Harris v. Forklift Systems, 510 U.S. 17 (1993)",
            "authority_type": "case",
            "binding_strength": 1.0
          }
        ],
        "authority_weight": 1.0
      }
    ],
    "provenance_summary": {
      "total_sources": 1,
      "unique_courts": 1,
      "authority_levels": ["supreme_court"],
      "confidence_range": [0.82, 0.95]
    }
  }
}
```

### Query Authority Hierarchy

Query legal authority hierarchy for a specific legal question.

```http
POST /api/v1/authority/hierarchy
```

**Request Body:**
```json
{
  "legal_question": "employment discrimination based on race",
  "jurisdiction": "US-CA",
  "include_analysis": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "employment discrimination based on race",
    "jurisdiction": "US-CA",
    "authorities": [
      {
        "authority_id": "cap:12345",
        "authority_type": "case",
        "citation": "McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)",
        "binding_strength": 1.0,
        "persuasive_strength": 0.0,
        "temporal_relevance": 0.85,
        "relevance_reasoning": [
          "Establishes burden-shifting framework for discrimination claims",
          "Supreme Court precedent binding on all federal and state courts",
          "Specifically addresses race discrimination in employment"
        ],
        "key_holdings": [
          "Prima facie case requires: (1) minority status, (2) qualification, (3) adverse action, (4) circumstances suggesting discrimination"
        ],
        "source_provenance": {
          "extraction_date": "2025-08-23T15:30:00Z",
          "confidence": 0.98,
          "method": "case_analysis"
        }
      }
    ],
    "analysis_metadata": {
      "search_time": "2025-08-23T15:30:00Z",
      "total_cases_searched": 1547,
      "total_statutes_searched": 23,
      "reasoning_engine_version": "1.0.0"
    }
  }
}
```

### Answer Legal Question

Answer legal question with full reasoning chain and citations.

```http
POST /api/v1/query/answer
```

**Request Body:**
```json
{
  "question": "What are the elements of a hostile work environment claim?",
  "jurisdiction": "US",
  "include_reasoning": true,
  "max_authorities": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "question": "What are the elements of a hostile work environment claim?",
    "jurisdiction": "US",
    "answer_summary": "A hostile work environment claim requires: (1) unwelcome conduct based on protected characteristic, (2) conduct was severe or pervasive, (3) conduct created abusive working environment, (4) employer knew or should have known of conduct",
    "confidence": 0.92,
    "reasoning_chain": [
      {
        "step_type": "legal_rule_application",
        "premises": ["title_vii_protection", "harassment_conduct"],
        "rule_applied": "hostile_environment_standard",
        "conclusion": "four_element_test",
        "supporting_authority": "Harris v. Forklift Systems, 510 U.S. 17 (1993)",
        "confidence": 0.95,
        "provenance_trace": {
          "source": "cap:67890",
          "paragraph": "cap:67890#¶8",
          "extraction_method": "legal_rule_extraction"
        }
      }
    ],
    "supporting_authorities": [
      {
        "citation": "Harris v. Forklift Systems, 510 U.S. 17 (1993)",
        "authority_type": "case",
        "binding_strength": 1.0,
        "key_text": "When the workplace is permeated with discriminatory intimidation, ridicule, and insult...",
        "provenance_trace": {
          "source_doc": "cap:67890",
          "extraction_confidence": 0.96
        }
      }
    ],
    "caveats": [
      "This analysis applies to federal law; state laws may vary",
      "Specific facts of each case affect application of these elements",
      "Recent developments in case law should be considered"
    ]
  }
}
```

## 🔗 Citation Resolution API

### Resolve Citation

Resolve citation text to source documents with provenance.

```http
POST /api/v1/citations/resolve
```

**Request Body:**
```json
{
  "citation_text": "Brown v. Board, 347 U.S. 483",
  "include_alternatives": true,
  "confidence_threshold": 0.8
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "input_citation": "Brown v. Board, 347 U.S. 483",
    "normalized_citation": "Brown v. Board of Education, 347 U.S. 483 (1954)",
    "resolution_confidence": 0.98,
    "candidates": [
      {
        "document_id": "cap:12345",
        "title": "Brown v. Board of Education of Topeka",
        "citation": "347 U.S. 483 (1954)",
        "confidence": 0.98,
        "resolution_method": "exact_match",
        "provenance_trace": {
          "source": "cap_dataset",
          "ingestion_date": "2025-08-23T12:00:00Z",
          "validation_status": "verified"
        },
        "document_metadata": {
          "decision_date": "1954-05-17",
          "court": "Supreme Court of the United States",
          "docket_number": "1",
          "word_count": 5342
        }
      }
    ]
  }
}
```

## 📊 Analytics & Metrics API

### Query Performance Metrics

Get performance metrics for query analysis.

```http
GET /api/v1/metrics/performance
```

**Parameters:**
- `time_range` (query): Time range for metrics (e.g., "24h", "7d", "30d")
- `metric_types` (query): Comma-separated list of metric types

**Response:**
```json
{
  "success": true,
  "data": {
    "time_range": "24h",
    "metrics": {
      "query_latency": {
        "p50": 450,
        "p95": 1200,
        "p99": 2800,
        "unit": "milliseconds"
      },
      "citation_resolution_rate": {
        "success_rate": 0.94,
        "total_attempts": 15420,
        "successful_resolutions": 14495
      },
      "data_quality": {
        "provenance_completeness": 0.98,
        "confidence_distribution": {
          "high_confidence": 0.85,
          "medium_confidence": 0.12,
          "low_confidence": 0.03
        }
      }
    }
  }
}
```

## 🛡️ Rate Limits & Quotas

### Rate Limiting
- **Free Tier**: 1,000 requests/day, 10 requests/minute
- **Pro Tier**: 100,000 requests/day, 1,000 requests/minute  
- **Enterprise**: Custom limits

### Response Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

## 📝 Error Codes

| Code | Description |
|------|-------------|
| `INVALID_ENTITY_ID` | Entity ID format is invalid |
| `ENTITY_NOT_FOUND` | Requested entity does not exist |
| `CITATION_NOT_RESOLVED` | Citation could not be resolved |
| `INSUFFICIENT_CONTEXT` | Not enough context for reasoning |
| `JURISDICTION_NOT_SUPPORTED` | Jurisdiction not supported |
| `QUERY_TOO_BROAD` | Query scope too broad, please narrow |
| `PROVENANCE_INCOMPLETE` | Incomplete provenance chain |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded |
| `UNAUTHORIZED` | Invalid or missing authentication |
| `INTERNAL_ERROR` | Internal server error |

## 🔌 Integration Examples

### Python SDK Example

```python
from openlaw_cap import CaselawClient

client = CaselawClient(api_key="your_api_key")

# Trace provenance
trace = client.provenance.trace("cap:12345#¶17")
print(f"Source documents: {len(trace.source_documents)}")

# Answer legal question
answer = client.query.answer(
    question="What is the burden of proof for discrimination?",
    jurisdiction="US",
    include_reasoning=True
)
print(f"Answer: {answer.summary}")
print(f"Authorities: {[a.citation for a in answer.authorities]}")

# Resolve citation
resolution = client.citations.resolve("347 U.S. 483")
if resolution.candidates:
    case = resolution.candidates[0]
    print(f"Resolved to: {case.title}")
```

### JavaScript/Node.js Example

```javascript
const { CaselawClient } = require('@openlaw/cap-client');

const client = new CaselawClient({ apiKey: 'your_api_key' });

// Retrieve with provenance
const results = await client.search.retrieve({
  query: 'hostile work environment',
  jurisdiction: 'US',
  k: 5
});

results.results.forEach(result => {
  console.log(`Case: ${result.source_citations[0].citation}`);
  console.log(`Relevance: ${result.relevance_score}`);
  console.log(`Authority: ${result.authority_weight}`);
});
```

This API provides comprehensive access to the CAP caselaw hypergraph with full provenance tracking, enabling downstream legal AI systems to trace every piece of information back to its original source with complete audit trails.