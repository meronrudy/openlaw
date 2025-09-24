# OpenLaw Legal Reasoning API — Example Test Calls
Implementation note: The backend reasoning engine defaults to the native path via [NativeLegalBridge](core/adapters/native_bridge.py:1). When ingesting raw text, use [doc_to_graph_cli.py](scripts/ingest/doc_to_graph_cli.py:1) to generate GraphML for the native bridge.

This document provides concrete example API invocations (HTTP/cURL) for a public/partner-facing Legal Analysis API built on the OpenLaw substrate. It demonstrates request/response payloads for single document analysis, batch analysis, enabling detailed reasoning, selecting domain plugins, and handling errors. Clickable references point to relevant code constructs:
- [LegalAnalysisCLI.analyze_document()](cli_driver.py:35)
- [LegalAnalysisCLI._format_json_output()](cli_driver.py:168)
- [Provenance()](core/model.py:15)
- [Context.is_applicable_in()](core/model.py:55)
- [Node()](core/model.py:77)
- [Hyperedge()](core/model.py:89)
- [RuleEngine()](core/reasoning.py:18)

Assumptions:
- Base URL: https://api.openlaw.example.com
- API version: v1
- API Key header: Authorization: Bearer <token>
- Endpoints (illustrative):
  - POST /v1/analyze
  - POST /v1/analyze/batch

-------------------------------------------------------------------------------

## 1) Analyze a Single Document (Employment Law)

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 7a6d9547-b55a-41bd-9c8e-1a2c78e0f123" \
  -d '{
    "text": "I am requesting reasonable accommodation under the ADA for my mobility disability...",
    "context": {
      "jurisdiction": "US",
      "law_type": "employment"
    },
    "options": {
      "format": "json",
      "show_reasoning": false
    },
    "plugin": "employment_law"
  }'
```

Response (200)
```json
{
  "api_version": "1.0",
  "analysis_time": "2025-09-14T09:00:00.123Z",
  "entities": [
    {
      "text": "reasonable accommodation",
      "type": "ADA_REQUEST",
      "start": 12,
      "end": 36,
      "confidence": 0.85,
      "metadata": { "category": "ada" }
    },
    {
      "text": "mobility disability",
      "type": "DISABILITY",
      "start": 74,
      "end": 92,
      "confidence": 0.85,
      "metadata": { "category": "ada" }
    }
  ],
  "citations": [
    {
      "text": "42 U.S.C. § 12112",
      "type": "LEGAL_CITATION",
      "confidence": 0.95,
      "metadata": {
        "citation_type": "statute",
        "normalized": "42 U.S.C. § 12112"
      }
    }
  ],
  "original_facts": [
    {
      "statement": "employee_has_disability",
      "entity_type": "DISABILITY",
      "disability_details": "mobility disability"
    }
  ],
  "derived_facts": [
    {
      "statement": "reasonable_accommodation_required",
      "derived_from": [
        "employee_has_disability",
        "can_perform_essential_functions_with_accommodation"
      ],
      "rule_authority": "42 U.S.C. § 12112(b)(5)(A)"
    }
  ],
  "conclusions": [
    {
      "type": "ADA_VIOLATION",
      "conclusion": "Employer may be required to provide reasonable accommodation",
      "legal_basis": "42 U.S.C. § 12112(b)(5)(A)",
      "confidence": 0.85,
      "fact_id": "reasonable_accommodation_required"
    }
  ],
  "provenance": {
    "source": [
      { "type": "document", "id": "req-uuid", "uri": null }
    ],
    "method": "forward_chaining",
    "agent": "openlaw.api",
    "time": "2025-09-14T09:00:00.123Z",
    "confidence": 0.85,
    "derivation": ["rule:ada_reasonable_accommodation"]
  }
}
```

Notes:
- The result shape mirrors what the CLI formatter emits via [LegalAnalysisCLI._format_json_output()](cli_driver.py:168), with provenance fields aligned to [Provenance()](core/model.py:15).
- Jurisdiction and law_type inform rule applicability via [Context.is_applicable_in()](core/model.py:55) and rule filtering in [RuleEngine()](core/reasoning.py:18).

-------------------------------------------------------------------------------

## 2) Analyze with Detailed Reasoning

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "FLSA violation: Employee worked 50 hours/week, paid for 40...",
    "context": { "jurisdiction": "US", "law_type": "employment" },
    "options": { "format": "json", "show_reasoning": true },
    "plugin": "employment_law"
  }'
```

Response (200, excerpt)
```json
{
  "api_version": "1.0",
  "reasoning": {
    "original_facts": [
      { "statement": "employee_worked_hours>40", "evidence": "50 hours" },
      { "statement": "overtime_compensation_missing", "evidence": "paid for 40" }
    ],
    "derived_facts": [
      {
        "statement": "overtime_entitlement",
        "rule_authority": "29 U.S.C. § 207",
        "premises": ["employee_worked_hours>40", "overtime_compensation_missing"]
      }
    ]
  },
  "conclusions": [
    {
      "type": "FLSA_VIOLATION",
      "conclusion": "Employee entitled to overtime compensation",
      "legal_basis": "29 U.S.C. § 207",
      "confidence": 0.90
    }
  ],
  "provenance": {
    "method": "forward_chaining",
    "agent": "openlaw.api",
    "confidence": 0.90,
    "derivation": ["rule:flsa_overtime_entitlement"]
  }
}
```

Notes:
- When `show_reasoning=true`, a reasoning section includes premises/derived facts, which are generated by internal rule application in [RuleEngine()](core/reasoning.py:18).

-------------------------------------------------------------------------------

## 3) Select Domain Plugin — Caselaw vs Employment

Request (Caselaw)
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "In Smith v. Jones, the court held that ...",
    "context": { "jurisdiction": "US", "law_type": "caselaw" },
    "options": { "format": "json", "show_reasoning": true },
    "plugin": "caselaw"
  }'
```

Response (200, excerpt)
```json
{
  "entities": [
    { "text": "Smith v. Jones", "type": "CASE_CITATION", "confidence": 0.94 }
  ],
  "citations": [
    { "text": "410 U.S. 113 (1973)", "type": "LEGAL_CITATION", "confidence": 0.96 }
  ],
  "conclusions": [
    {
      "type": "PRECEDENTIAL_HOLDING",
      "conclusion": "Identified holding relevant to jurisdiction/timeframe",
      "legal_basis": "Case law authority"
    }
  ]
}
```

Notes:
- Plugin behavior is routed via the SDK contracts ([OntologyProvider](sdk/plugin.py:28), [MappingProvider.extract_entities()](sdk/plugin.py:75), [RuleProvider.statutory_rules()](sdk/plugin.py:129)).

-------------------------------------------------------------------------------

## 4) Batch Analyze up to 25 Documents

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze/batch" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "id": "doc-1",
        "text": "ADA request: ergonomic chair and modified schedule...",
        "context": { "jurisdiction": "US", "law_type": "employment" },
        "plugin": "employment_law",
        "options": { "format": "json" }
      },
      {
        "id": "doc-2",
        "text": "FLSA complaint: 52 hours worked, paid straight time only...",
        "context": { "jurisdiction": "US", "law_type": "employment" },
        "plugin": "employment_law",
        "options": { "format": "json", "show_reasoning": true }
      }
    ]
  }'
```

Response (200, partial)
```json
{
  "api_version": "1.0",
  "results": [
    {
      "id": "doc-1",
      "status": 200,
      "entities": [{ "text": "ergonomic chair", "type": "REASONABLE_ACCOMMODATION" }],
      "conclusions": [{ "type": "ADA_VIOLATION", "confidence": 0.85 }]
    },
    {
      "id": "doc-2",
      "status": 200,
      "reasoning": {
        "original_facts": [{ "statement": "employee_worked_hours>40" }],
        "derived_facts": [{ "statement": "overtime_entitlement" }]
      },
      "conclusions": [{ "type": "FLSA_VIOLATION", "confidence": 0.90 }]
    }
  ],
  "errors": []
}
```

Notes:
- Partial failures should be reported per item with `"status": <http-code>` and an `"error"` block if any item fails.

-------------------------------------------------------------------------------

## 5) Error Handling — Invalid Plugin

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Some text...",
    "context": { "jurisdiction": "US" },
    "plugin": "unknown_domain",
    "options": { "format": "json" }
  }'
```

Response (400)
```json
{
  "error": true,
  "code": "INVALID_PLUGIN",
  "message": "Unsupported plugin: unknown_domain",
  "hint": "Valid values: employment_law, caselaw",
  "request_id": "req-1a2b3c"
}
```

-------------------------------------------------------------------------------

## 6) Error Handling — Missing Text

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"context": { "jurisdiction": "US" }, "plugin": "employment_law"}'
```

Response (400)
```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "message": "Field 'text' is required",
  "request_id": "req-abc123"
}
```

-------------------------------------------------------------------------------

## 7) Idempotent Retries with Idempotency-Key

Request (retry-safe)
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 7a6d9547-b55a-41bd-9c8e-1a2c78e0f123" \
  -d '{
    "text": "ADA request text ...",
    "context": { "jurisdiction": "US", "law_type": "employment" },
    "options": { "format": "json" },
    "plugin": "employment_law"
  }'
```

Notes:
- The server returns the original response for duplicate keys received within a defined window. Attach the key in provenance if desired (e.g., provenance.source → request metadata) aligned with [Provenance()](core/model.py:15).

-------------------------------------------------------------------------------

## 8) Minimal Client Example (Python requests)

```python
import requests

url = "https://api.openlaw.example.com/v1/analyze"
headers = {
    "Authorization": f"Bearer {OPENLAW_TOKEN}",
    "Content-Type": "application/json",
    "Idempotency-Key": "7a6d9547-b55a-41bd-9c8e-1a2c78e0f123"
}
payload = {
    "text": "Employee requests reasonable accommodation under ADA...",
    "context": { "jurisdiction": "US", "law_type": "employment" },
    "options": { "format": "json", "show_reasoning": True },
    "plugin": "employment_law"
}
resp = requests.post(url, json=payload, headers=headers, timeout=30)
resp.raise_for_status()
data = resp.json()
print(data["conclusions"])
```

-------------------------------------------------------------------------------

## 9) Mapping to Core Models

- Results are contractually aligned to the OpenLaw core:
  - Nodes and edges semantics map to [Node()](core/model.py:77) and [Hyperedge()](core/model.py:89).
  - Legal context — jurisdiction/temporal — verified via [Context.is_applicable_in()](core/model.py:55).
  - Reasoning and explanations derived via [RuleEngine()](core/reasoning.py:18) and plugin explainers.

-------------------------------------------------------------------------------

## 10) Operational Guidelines

- Timeouts: 30s per request recommended for synchronous analysis of short documents. For long documents or bulk workloads, prefer batch or job-processing patterns.
- Rate limits: per-tenant quotas; 429 returned on overage.
- Observability: include a `request_id` in every response; optionally link into provenance metadata (agent/source) as per [Provenance()](core/model.py:15).
- Versioning: use `/v1/` path prefix; include `"api_version"` field in every response envelope.

-------------------------------------------------------------------------------

These examples are directly grounded in the OpenLaw CLI behavior and core types; see [LegalAnalysisCLI.analyze_document()](cli_driver.py:35) for the reference flow and [LegalAnalysisCLI._format_json_output()](cli_driver.py:168) for the JSON output shape.