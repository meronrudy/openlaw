# API User Stories and Ideal Implementations
This document captures user stories for the OpenLaw-based Legal Analysis API:
- OpenLaw-based synchronous Legal Analysis API (public/partner-facing) — backed by the Native Engine and [NativeLegalBridge](core/adapters/native_bridge.py:1)

Where relevant, clickable references to code are included using project constructs like:
- [Provenance()](core/model.py:15)
- [Context.is_applicable_in()](core/model.py:55)
- [Node()](core/model.py:77)
- [Hyperedge()](core/model.py:89)
- [RuleEngine()](core/reasoning.py:18)
- [LegalAnalysisCLI.analyze_document()](cli_driver.py:35)
- [OntologyProvider](sdk/plugin.py:28)
- [MappingProvider.extract_entities()](sdk/plugin.py:75)
- [RuleProvider.statutory_rules()](sdk/plugin.py:129)
- [LegalExplainer.statutory_explanation()](sdk/plugin.py:177)

-------------------------------------------------------------------------------

## Epic A — Public/Partner-Facing Legal Analysis API (OpenLaw)

### Story A1 — Submit a legal document for analysis
As a partner application developer, I want to POST a document and jurisdiction to get legal entities, citations, and conclusions, so that I can embed explainable employment law analysis in my product.

- Acceptance:
  - POST /v1/analyze accepts: 
    - { text, context: { jurisdiction, valid_from?, valid_to?, law_type? }, options: { format: summary|detailed|json, show_reasoning? }, plugin: employment_law|caselaw }
  - Returns 200 with JSON containing entities, citations, original_facts, derived_facts, conclusions, and provenance standardized to [Provenance()](core/model.py:15).
  - Validation errors → 400. Idempotency-Key header deduplicates within 24h.
- Ideal Implementation:
  - FastAPI service; model contracts from Pydantic reflecting [Provenance()](core/model.py:15), [Context()](core/model.py:45), [Node()](core/model.py:77).
  - Invoke plugin pipeline directly (preferable) or reuse [LegalAnalysisCLI.analyze_document()](cli_driver.py:35) serialization pattern, mirroring [_format_json_output()](cli_driver.py:168).
  - Select plugin via loader registry (see SDK interfaces: [OntologyProvider](sdk/plugin.py:28), [MappingProvider.extract_entities()](sdk/plugin.py:75), [RuleProvider.statutory_rules()](sdk/plugin.py:129), [LegalExplainer.statutory_explanation()](sdk/plugin.py:177)).

### Story A2 — Retrieve detailed reasoning and explanations
As a legal analyst, I want detailed reasoning chains and explanations, so I can review why each conclusion was derived.

- Acceptance:
  - options.show_reasoning=true includes:
    - original_facts and derived_facts with rule_authority, confidence, and derivations
    - human‑readable explanations tied to statutory/case authority
  - Confidence values present and explainable.
- Ideal Implementation:
  - Use [RuleEngine()](core/reasoning.py:18) outputs and explainer provided by domain plugin [LegalExplainer.statutory_explanation()](sdk/plugin.py:177). Embed derivation trail into [Provenance()](core/model.py:15).

### Story A3 — Select legal domain per request
As a platform integrator, I want to specify which legal domain plugin to use, so one API can serve multiple verticals.

- Acceptance:
  - plugin param supports "employment_law" and "caselaw"; invalid → 400; unavailable → 503.
- Ideal Implementation:
  - Plugin registry + manifest validation; route to correct provider interfaces (SDK), persist domain choice in response envelope.

### Story A4 — Batch analyze a small set
As an operations user, I want to POST up to 25 docs synchronously for quick evaluation.

- Acceptance:
  - POST /v1/analyze/batch → array of per-document responses; partial failures reported with per-item status.
- Ideal Implementation:
  - Multi-process worker pool with bounded concurrency; reuse single-document pipeline; return HTTP 200 with per-item statuses.

### Story A5 — Versioning and schema evolution
As a platform owner, I want stable, versioned endpoints and schemas.

- Acceptance:
  - Versioned paths (/v1/…), response includes api_version, changelogs available.
- Ideal Implementation:
  - Generate OpenAPI from the same Pydantic models used by core: [Provenance()](core/model.py:15), [Context()](core/model.py:45), [Node()](core/model.py:77).

### Story A6 — Security, quotas, and observability
As a security engineer, I want auth, quotas, and traceability.

- Acceptance:
  - API keys/OAuth2, tenant quotas, 429 on overage; request IDs; full audit logs; attach request ID to provenance metadata.
- Ideal Implementation:
  - Gateway with authN/Z, rate limiters; OpenTelemetry tracing; store request metadata inside provenance (source/agent fields of [Provenance()](core/model.py:15)).

-------------------------------------------------------------------------------

## Proposed API Contracts (Sketch)

### OpenLaw — Analyze (sync)
- Request
```json
{
  "text": "string",
  "context": {
    "jurisdiction": "US",
    "valid_from": null,
    "valid_to": null,
    "law_type": "employment"
  },
  "options": {
    "format": "json",
    "show_reasoning": true
  },
  "plugin": "employment_law"
}
```
- Response
```json
{
  "api_version": "1.0",
  "entities": [],
  "citations": [],
  "original_facts": [],
  "derived_facts": [],
  "conclusions": [],
  "explanations": [],
  "provenance": {
    "source": [],
    "method": "forward_chaining",
    "agent": "openlaw.api",
    "time": "2025-09-14T00:00:00Z",
    "confidence": 0.85,
    "derivation": []
  }
}
```


-------------------------------------------------------------------------------

## Why this API?
- Public/partner legal analysis (OpenLaw) benefits from Pydantic models, provenance-first results, domain plugins, and synchronous JSON workflows aligning with legal practitioner needs.

-------------------------------------------------------------------------------

## Implementation Checklist

- OpenLaw API
  - [ ] Define Pydantic request/response models mirroring [Provenance()](core/model.py:15) and [Context()](core/model.py:45)
  - [ ] Implement /v1/analyze and /v1/analyze/batch; integrate plugin selection
  - [ ] Generate OpenAPI; add examples; implement auth and quotas
  - [ ] Add correlation IDs to provenance.agent or source metadata
  - [ ] CI with 112+ unit tests including API layer tests

-------------------------------------------------------------------------------

## Final Guidance
- If your API serves legal document analysis to end users or partners, base it on OpenLaw’s models and plugin architecture. It is API‑ready and explainability/provenance‑complete.