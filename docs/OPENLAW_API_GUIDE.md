# OpenLaw API Guide
Comprehensive user documentation for the OpenLaw Legal Reasoning API, including robust legal reasoning examples, a getting-started tutorial, a free “Try the API” playground endpoint, and a Graphviz-based visualization layer for reasoning chains and provenance.

This API exposes explainable legal analysis based on a provenance-first legal ontology hypergraph. It returns entities, legal citations, derived facts, conclusions with confidence, and provenance trails suitable for audit and review. The visualization layer renders these results as clustered PNG diagrams.

Implementation note: The default reasoning path uses the Native Engine via [NativeLegalBridge](core/adapters/native_bridge.py:1). Legacy hypergraph [RuleEngine()](core/reasoning.py:18) references are maintained for backward compatibility in select modules.
Key code references:
- Ingestion CLI: [doc_to_graph_cli.py](scripts/ingest/doc_to_graph_cli.py:1) converts text → GraphML for native ingestion
- CLI flow: [LegalAnalysisCLI.analyze_document()](cli_driver.py:35)
- JSON formatting: [LegalAnalysisCLI._format_json_output()](cli_driver.py:168)
- Core models: [Provenance()](core/model.py:15), [Context.is_applicable_in()](core/model.py:55), [Node()](core/model.py:77), [Hyperedge()](core/model.py:89)
- Rule engine (legacy hypergraph): [RuleEngine()](core/reasoning.py:18)
- Native bridge (default entry): [core/adapters/native_bridge.py](core/adapters/native_bridge.py:1)
- Native engine facade: [NativeLegalFacade.run_reasoning()](core/native/facade.py:74)
- Visualization module: [visualize_analysis()](viz/graphviz_renderer.py:1) (PNG renderer)

See also:
- Example API calls: [OPENLAW_API_EXAMPLES.md](docs/OPENLAW_API_EXAMPLES.md:1)
- API User Stories & Ideal Implementations: [API_USER_STORIES.md](docs/API_USER_STORIES.md:1)

-------------------------------------------------------------------------------

## 1) Overview

- Base URL (example): https://api.openlaw.example.com
- Versioning: All endpoints are prefixed with a version, e.g., /v1/…
- Authentication: Bearer token in Authorization header (unless using the free Playground)
- Formats: JSON requests and JSON responses
- Rate Limits: Applied per tenant; 429 on overage
- Provenance: Every analysis returns provenance aligned to [Provenance()](core/model.py:15)
- Plugins: Select analysis domain via plugin parameter, e.g., employment_law or caselaw
- Visualization: Graphviz PNG diagrams available via CLI flag (--viz) or Python API ([visualize_analysis()](viz/graphviz_renderer.py:1))

-------------------------------------------------------------------------------

## 2) Quick Start Tutorial

### 2.1 Obtain API Credentials
- Sign up on the OpenLaw developer portal
- Create an API key; store securely
- Local testing:

```bash
export OPENLAW_TOKEN="your-api-key"
```

### 2.2 First Request (Employment Law — ADA)

Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/analyze" \
  -H "Authorization: Bearer $OPENLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I request reasonable accommodation under the ADA for a mobility disability...",
    "context": { "jurisdiction": "US", "law_type": "employment" },
    "options": { "format": "json", "show_reasoning": true },
    "plugin": "employment_law"
  }'
```

Response (abridged)
```json
{
  "api_version": "1.0",
  "analysis_time": "2025-09-14T09:00:00.123Z",
  "entities": [
    { "text": "reasonable accommodation", "type": "ADA_REQUEST", "confidence": 0.85 },
    { "text": "mobility disability", "type": "DISABILITY", "confidence": 0.85 }
  ],
  "citations": [
    { "text": "42 U.S.C. § 12112", "type": "LEGAL_CITATION", "confidence": 0.95 }
  ],
  "reasoning": {
    "original_facts": [
      { "statement": "employee_has_disability" },
      { "statement": "can_perform_essential_functions_with_accommodation" }
    ],
    "derived_facts": [
      {
        "statement": "reasonable_accommodation_required",
        "rule_authority": "42 U.S.C. § 12112(b)(5)(A)"
      }
    ]
  },
  "conclusions": [
    {
      "type": "ADA_VIOLATION",
      "conclusion": "Employer may be required to provide reasonable accommodation",
      "legal_basis": "42 U.S.C. § 12112(b)(5)(A)",
      "confidence": 0.85
    }
  ],
  "provenance": {
    "source": [{ "type": "document", "id": "req-uuid" }],
    "method": "forward_chaining",
    "agent": "openlaw.api",
    "time": "2025-09-14T09:00:00.123Z",
    "confidence": 0.85,
    "derivation": ["rule:ada_reasonable_accommodation"]
  }
}
```

Schema alignment:
- JSON: [LegalAnalysisCLI._format_json_output()](cli_driver.py:168)
- Context filtering: [Context.is_applicable_in()](core/model.py:55)
- Inference: [RuleEngine()](core/reasoning.py:18)

### 2.3 Minimal Python Client
```python
import requests
payload = {
  "text": "Employee requests reasonable accommodation under ADA...",
  "context": {"jurisdiction": "US", "law_type": "employment"},
  "options": {"format": "json", "show_reasoning": True},
  "plugin": "employment_law"
}
resp = requests.post(
  "https://api.openlaw.example.com/v1/analyze",
  headers={"Authorization": f"Bearer {OPENLAW_TOKEN}", "Content-Type": "application/json"},
  json=payload,
  timeout=30
)
resp.raise_for_status()
print(resp.json()["conclusions"])
```

-------------------------------------------------------------------------------

## 3) Endpoints

### 3.1 POST /v1/analyze
Analyze a single document with a specified domain plugin.

Request body
```json
{
  "text": "string — legal document text",
  "context": {
    "jurisdiction": "US",
    "valid_from": null,
    "valid_to": null,
    "law_type": "employment"
  },
  "options": {
    "format": "json | detailed | summary",
    "show_reasoning": true
  },
  "plugin": "employment_law | caselaw"
}
```

Response body (high-level)
```json
{
  "api_version": "1.0",
  "analysis_time": "ISO-8601",
  "entities": [ ... ],
  "citations": [ ... ],
  "original_facts": [ ... ],
  "derived_facts": [ ... ],
  "conclusions": [ ... ],
  "explanations": [ ... ],
  "provenance": { ... }
}
```

Notes
- Provenance adheres to [Provenance()](core/model.py:15)
- Nodes/edges semantics are consistent with [Node()](core/model.py:77) and [Hyperedge()](core/model.py:89)

### 3.2 POST /v1/analyze/batch
Analyze multiple documents synchronously (N ≤ 25). Returns a results array with per-item status and errors if any.

### 3.3 GET /v1/health
Health/status probe for operational monitoring.

-------------------------------------------------------------------------------

## 4) Authentication, Rate Limits, and Idempotency

- Auth: Authorization: Bearer <token>
- Rate Limits: Per tenant; 429 Too Many Requests with Retry-After header
- Idempotency: Provide Idempotency-Key to safely retry the same request. The server returns the original response if the key matches a recent identical request.

Example
```bash
-H "Idempotency-Key: 7a6d9547-b55a-41bd-9c8e-1a2c78e0f123"
```

-------------------------------------------------------------------------------

## 5) Robust Legal Reasoning Examples

### 5.1 ADA Reasonable Accommodation (Employment Law)
Input
```
I request reasonable accommodation under ADA for a chronic joint condition ...
Requested accommodations: ergonomic chair, modified work schedule ...
```

Expected
- Entities:
  - ADA_REQUEST: “reasonable accommodation”, “ADA”
  - DISABILITY: “joint condition”
  - REASONABLE_ACCOMMODATION: “ergonomic chair”, “modified work schedule”
- Citations: 42 U.S.C. § 12112
- Reasoning:
  - original_facts: “employee_has_disability”, “can_perform_essential_functions_with_accommodation”
  - derived_facts: “reasonable_accommodation_required” (authority 42 U.S.C. § 12112(b)(5)(A))
- Conclusion:
  - ADA_VIOLATION — Employer may be required to provide reasonable accommodation
- Provenance:
  - method: forward_chaining; derivation includes ADA rule identifiers

### 5.2 FLSA Overtime Entitlement
Input
```
Employee worked 52 hours in a week and was paid straight-time only ...
```
Expected
- Entities: OVERTIME (hours > 40), FLSA_VIOLATION cues
- Citations: 29 U.S.C. § 207
- Reasoning: “employee_worked_hours>40” + “overtime_compensation_missing” ⇒ “overtime_entitlement”
- Conclusion: FLSA_VIOLATION — Employee entitled to overtime compensation

### 5.3 Wrongful Termination (Public Policy Exception)
Input
```
I filed an OSHA complaint; five days later I was terminated for supposed performance issues...
```
Expected
- Entities: WHISTLEBLOWING, RETALIATION, WRONGFUL_TERMINATION, PUBLIC_POLICY_EXCEPTION
- Conclusion: WRONGFUL_TERMINATION — Potential claim under public policy exception

### 5.4 Workers' Compensation Claim and Retaliation
Input
```
Workplace injury; ER visit; MRI shows herniated disc; lost wages reported; retaliatory threats...
```
Expected
- Entities: WORKERS_COMP_CLAIM, MEDICAL_TREATMENT, LOST_WAGES, RETALIATION
- Conclusions:
  - WORKERS_COMP_ENTITLEMENT: Valid claim
  - RETALIATION_VIOLATION: Retaliation prohibited

-------------------------------------------------------------------------------

## 6) “Try the API” Playground Endpoint

- Endpoint: POST /v1/try/analyze
- Auth: None (or lightweight token); strict rate limits (e.g., 5 req/min/IP)
- Limits:
  - Document length ≤ 5,000 chars
  - plugin: "employment_law" only
  - options.show_reasoning defaults true; abridged fields returned
- CORS: Enabled for *.openlaw.example.com docs and developer portals
- Response Time Target: < 2s P50 for small docs

Example Request
```bash
curl -X POST "https://api.openlaw.example.com/v1/try/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I request reasonable accommodation under ADA...",
    "context": { "jurisdiction": "US", "law_type": "employment" }
  }'
```

Example Response (abridged)
```json
{
  "api_version": "1.0",
  "entities": [
    { "text": "reasonable accommodation", "type": "ADA_REQUEST", "confidence": 0.85 }
  ],
  "reasoning": {
    "original_facts": [{ "statement": "employee_has_disability" }],
    "derived_facts": [{ "statement": "reasonable_accommodation_required" }]
  },
  "conclusions": [
    { "type": "ADA_VIOLATION", "confidence": 0.85 }
  ]
}
```

-------------------------------------------------------------------------------

## 7) Visualization Layer (Graphviz PNG)

OpenLaw provides a minimal Graphviz-based renderer for analysis results. It produces static PNG images to visually explore entities, reasoning chains (original and derived facts), citations, and conclusions.

### 7.1 Installation Requirements

- Python dependency (already added): graphviz≥0.20.3
  - See [requirements.txt](requirements.txt:1)
- System Graphviz binary required (dot must be on PATH)
  - macOS: `brew install graphviz`
  - Ubuntu/Debian: `sudo apt-get install graphviz`
  - Windows: install Graphviz MSI and add to PATH

If the Python package or system binary is missing, visualization is skipped with a warning.

### 7.2 Module API

Renderer module: [viz/graphviz_renderer.py](viz/graphviz_renderer.py:1)

- [visualize_analysis()](viz/graphviz_renderer.py:1)
  - Signature
    - visualize_analysis(analysis: Dict[str, Any], source_document_path: Optional[str] = None, out_path: Optional[str] = None, filename_prefix: Optional[str] = None, format: str = "png") -> str
  - Inputs
    - analysis: Analysis dictionary matching our internal results (see Data Structure below)
    - source_document_path: Determines default output directory if out_path is not provided
    - out_path: Explicit output directory (created if missing)
    - filename_prefix: Overrides the default filename base
    - format: PNG by default (minimal renderer); accepts "png"
  - Output
    - Absolute path to the generated PNG file (e.g., `.../document.openlaw.png`)
  - Diagram content
    - Cluster “Entities” — entity type + text
    - Cluster “Original Facts” — statements used as premises
    - Cluster “Derived Facts” — derived statements and rule_authority if present
    - Cluster “Conclusions” — conclusion type, short conclusion text, legal_basis
    - Cluster “Citations” — citation text nodes
    - Edges
      - original_facts → derived_facts (from derived_facts[].derived_from)
      - derived_facts → conclusions (simple linkage)
      - citations → conclusions (authority references)
  - Confidence display
    - Confidence values are not rendered as numeric badges in v1 minimal diagram, but can be added later (see Extensibility)

- visualize_reasoning_chain()
  - Status: Planned
  - Purpose: Provide a focused subgraph for a single conclusion’s reasoning chain (premises → derived steps → conclusion) with optional filtering and depth controls.
  - Proposed signature (not yet implemented)
    - visualize_reasoning_chain(analysis: Dict[str, Any], conclusion_index: int = 0, ...) -> str

### 7.3 CLI Integration

- Analyze command flag: `--viz`
  - Enables PNG rendering after analysis completes
  - See [LegalAnalysisCLI.analyze_document()](cli_driver.py:35)
- Current flags (implemented)
  - `--viz` (boolean)
- Planned flag (next release)
  - `--viz-format` (string, e.g., png|svg). The renderer already supports a `format` parameter; the CLI flag will expose it once implemented.

Examples
```bash
# Summary + PNG saved next to input
python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt --format summary --viz

# Detailed + PNG
python cli_driver.py analyze --file test_documents/employment_law/flsa_overtime_complaint.txt --format detailed --show-reasoning --viz
```

Output
- The PNG is saved next to the input file by default (or in --out when exposed)
- Naming convention: `<document-stem>.openlaw.png`
  - E.g., `ada_accommodation_request.openlaw.png`

### 7.4 Programmatic Usage

```python
from viz.graphviz_renderer import visualize_analysis

# Suppose `analysis` is the "analysis_results" dict returned by CLI JSON or plugin API
png_path = visualize_analysis(
    analysis=analysis,
    source_document_path="test_documents/employment_law/ada_accommodation_request.txt",  # to place PNG next to input
    # out_path="out/graphs",                        # optional override
    # filename_prefix="my_ada_case",                # optional filename base
    # format="png"                                  # png only in minimal build
)
print("Visualization saved at:", png_path)
```

### 7.5 Data Structure Requirements (Input)

The minimal renderer expects the analysis dictionary to contain:
```json
{
  "entities": [ { "text": "string", "type": "string", "confidence": 0.0, "metadata": { ... } } ],
  "citations": [ { "text": "string", "type": "LEGAL_CITATION", "confidence": 0.0, "metadata": { "citation_type": "statute|case|...", "normalized": "..." } } ],
  "original_facts": [ { "statement": "string", ... } ],
  "derived_facts": [ { "statement": "string", "derived_from": ["fact_statement", ...], "rule_authority": "string" } ],
  "conclusions": [ { "type": "string", "conclusion": "string", "legal_basis": "string", "confidence": 0.0 } ]
}
```

Notes
- Missing sections are tolerated; they will simply render empty clusters
- For best results, include `derived_from` in `derived_facts` and `legal_basis` in `conclusions`

### 7.6 Extensibility and Roadmap

- Confidence Annotations: Add confidence scores as edge labels or node badges (planned)
- SVG Output + Tooltips: Allow `--viz-format svg` with mouseover tooltips (authority, confidence, citation details)
- Focused Chains: [visualize_reasoning_chain()] to target a single conclusion for clarity
- JSON → HTML Tree Viewer: Parallel export to a structured JSON for a web-based viewer (e.g., json2tree) — consistent with the same analysis schema
- Filtering Controls: Optional CLI flags to limit node counts, hide specific clusters, or select which conclusions to render

-------------------------------------------------------------------------------

## 8) Error Handling

Standardized error envelope:
```json
{
  "error": true,
  "code": "VALIDATION_ERROR | INVALID_PLUGIN | RATE_LIMITED | INTERNAL_ERROR",
  "message": "Human-readable message",
  "request_id": "req-uuid",
  "hint": "Optional remediation hint"
}
```

Examples
- Invalid plugin:
  - code: INVALID_PLUGIN, hint: “Valid values: employment_law, caselaw”
- Missing text:
  - code: VALIDATION_ERROR, message: “Field 'text' is required”
- Rate limit exceeded:
  - code: RATE_LIMITED, Retry-After header

-------------------------------------------------------------------------------

## 9) OpenAPI and Schemas

We recommend generating OpenAPI specs from the Pydantic models used internally. The response payload closely follows what the CLI emits via [LegalAnalysisCLI._format_json_output()](cli_driver.py:168), and aligns with:
- Provenance schema: [Provenance()](core/model.py:15)
- Context schema: [Context.is_applicable_in()](core/model.py:55)
- Knowledge graph semantics: [Node()](core/model.py:77), [Hyperedge()](core/model.py:89)

Illustrative OpenAPI snippet
```yaml
openapi: 3.0.3
info:
  title: OpenLaw Legal Reasoning API
  version: "1.0"
paths:
  /v1/analyze:
    post:
      summary: Analyze a legal document
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/AnalyzeRequest"
      responses:
        "200":
          description: Analysis result
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/AnalyzeResponse"
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
  schemas:
    AnalyzeRequest:
      type: object
      required: [text, plugin]
      properties:
        text: { type: string }
        context:
          type: object
          properties:
            jurisdiction: { type: string }
            valid_from: { type: string, format: date-time, nullable: true }
            valid_to: { type: string, format: date-time, nullable: true }
            law_type: { type: string }
        options:
          type: object
          properties:
            format: { type: string, enum: [json, detailed, summary] }
            show_reasoning: { type: boolean }
        plugin: { type: string, enum: [employment_law, caselaw] }
    AnalyzeResponse:
      type: object
      properties:
        api_version: { type: string }
        analysis_time: { type: string, format: date-time }
        entities: { type: array, items: { type: object } }
        citations: { type: array, items: { type: object } }
        original_facts: { type: array, items: { type: object } }
        derived_facts: { type: array, items: { type: object } }
        conclusions: { type: array, items: { type: object } }
        explanations: { type: array, items: { type: object } }
        provenance: { type: object }
```

-------------------------------------------------------------------------------

## 10) Best Practices

- Keep documents concise for single-call analysis; for large corpora, use batch or async pipelines
- Provide jurisdiction and dates when known (improves rule applicability via [Context.is_applicable_in()](core/model.py:55))
- Persist request IDs and response provenance for audits
- Prefer show_reasoning=true in development; disable in production UIs unless needed
- For visualization:
  - Ensure system Graphviz “dot” is installed
  - Use --viz for quick PNGs; in future, use --viz-format svg for interactive diagrams

-------------------------------------------------------------------------------

## 11) Changelog and Versioning

- api_version is included in responses for client-side handling
- Major changes are released under a new path v2 with migration notes
- Minor additions follow additive, backward-compatible rules

-------------------------------------------------------------------------------

## 12) Related Docs

- Examples: [OPENLAW_API_EXAMPLES.md](docs/OPENLAW_API_EXAMPLES.md:1)
- User Stories & Implementations: [API_USER_STORIES.md](docs/API_USER_STORIES.md:1)
- Plugin Development: [PLUGIN_DEVELOPMENT_GUIDE.md](docs/PLUGIN_DEVELOPMENT_GUIDE.md:1)

-------------------------------------------------------------------------------

## 13) FAQ

- Q: Does the API store my documents?
  - A: By default, no. We process in-memory and discard inputs. Persistence is opt-in and disclosed.

- Q: Can I customize rules?
  - A: Yes, via domain plugins defined against SDK interfaces such as [OntologyProvider](sdk/plugin.py:28), [RuleProvider](sdk/plugin.py:121), and [LegalExplainer](sdk/plugin.py:169).

- Q: What about latency?
  - A: Short documents typically return < 1–2s P50. Larger documents or complex domains may take longer. Use batch/async for heavy workloads.

- Q: How do I get PNG visualizations?
  - A: Install python-graphviz and the system Graphviz binary, then run:
    - `python cli_driver.py analyze --file <path> --viz`
    - Or call [visualize_analysis()](viz/graphviz_renderer.py:1) programmatically with the analysis dict.