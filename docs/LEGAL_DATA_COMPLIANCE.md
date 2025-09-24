Legal Data Handling and Compliance Guide

Purpose
- Define controls for handling legal documents and derived facts in the native legal reasoning system.
- Ensure privacy-by-default, jurisdiction-aware residency, auditable transformations, and safe exports.

Scope
- Applies to document ingestion, graph construction, reasoning, and interpretation export.
- Covers PII handling, redaction, residency constraints, auditing, config management, and operational checklists.

System touchpoints
- Reasoning Facade and export
  - Privacy defaults, filtered exports, audit trace controls:
    - [core/native/facade.py](core/native/facade.py)
    - [core/native/interpretation.py](core/native/interpretation.py)
- Bridge and configuration plumbing
  - Redaction config and compliance toggles:
    - [core/adapters/native_bridge.py](core/adapters/native_bridge.py)
- NLP pipeline for entity extraction
  - PII and citation normalization inputs:
    - [nlp/legal_ner.py](nlp/legal_ner.py)

Data classification and tagging
- PII classes
  - pii_basic: names, contact info, addresses.
  - pii_sensitive: SSN, financial account, medical data.
  - pii_case_specific: complainant/respondent identifiers, case numbers when sensitive by policy.
- Metadata tags (recommended on graph attributes)
  - data_tags: ["pii_basic" | "pii_sensitive" | "pii_case_specific"]
  - residency: ["US", "EU", "CA", ...] indicates origin/residency constraints
  - provenance: document source refs; avoid raw text persistence in the graph; prefer doc_id references.

Privacy-by-default posture
- Default behavior (production)
  - Do not persist raw document text in the graph store.
  - Store hashed party identifiers or opaque party_id references; avoid literal names unless whitelisted.
  - Emit filtered interpretations (see Export Policies) without sensitive attributes by default.
- Developer/auditor overrides
  - Explicit opt-in flags may enable full traces with caution for audit environments only.
  - Ensure these flags are never enabled in production CI pipelines.

Redaction policies (configurable)
- Redaction config (YAML)
  - Path: recommended config/compliance/redaction_rules.yml (referenced by redaction_cfg_path in [core/adapters/native_bridge.py](core/adapters/native_bridge.py))
  - Example structure:
    redact:
      node_attrs:
        - "name"
        - "email"
        - "address"
        - "ssn"
      edge_attrs:
        - "message_text"
        - "attachment_content"
      labels_blocklist:
        - "raw_document_text"
      pii_tags_blocklist:
        - "pii_sensitive"
    allowlist:
      node_attrs:
        - "party_id"
        - "doc_id"
      labels_allow:
        - "cites"
        - "same_issue"
- Enforcement points
  - During graph assembly (bridge ingestion), apply redaction rules before any persistence.
  - During export (interpretation.get_dict), drop redacted attributes and blocklisted labels.

Residency and access control
- Residency guardrails
  - Enforce that derived facts with residency: EU are not exported to non-EU targets unless explicit allow-list is present.
  - Maintain per-attribute residency tags; derived facts inherit the strictest residency from inputs.
- Access policy
  - Define consumer roles (ops, auditor, product, external).
  - Map roles to export profiles (see Export policies).
  - Block access when residency and role constraints conflict.

Export policies and filtered views
- Export profiles
  - default_profile (production):
    - No PII attributes
    - No sensitive labels
    - Only statement keys and probability intervals
  - audit_profile (restricted):
    - Includes enriched provenance and clause-level traces without raw payloads
    - Requires explicit flag and approval
- Implementation guidance
  - Interpretation should provide an export(filter_profile: str = "default_profile") that enforces these rules.
  - For backward compatibility, Interpretation.get_dict() should default to default_profile behavior.

Audit logging
- What to log
  - Reasoning configuration (engine version, burden function, style weights, jurisdiction)
  - Dataset identifiers (graph IDs, doc_id counts, residency distribution)
  - Export profile used and redaction ruleset version hash
- Where to log
  - Structured JSON logs or an audit sink (e.g., append-only datastore)
  - Do not log PII payloads; prefer stable identifiers/hashes
- Trace control
  - Atom-level traces should exclude raw text; only include label names and IDs

NLP and ingestion pipeline guardrails
- NLP outputs from [nlp/legal_ner.py](nlp/legal_ner.py) must:
  - Mark entities with pii tags where applicable (e.g., PERSON as pii_basic, FIN_ACCOUNT as pii_sensitive)
  - Normalize citations to court/jurisdiction/year; do not include raw excerpts in stored attributes
  - Provide doc_id and section/offset references instead of raw content payloads
- Ingestion mapping (doc -> graph)
  - The doc_to_graph step must apply:
    - Redaction rules (drop or hash sensitive values)
    - Residency tag assignment at attribute level
    - Provenance assignment (doc_id only)

Jurisdiction-aware reasoning and outputs
- Jurisdiction selection
  - The builder and bridge accept jurisdiction inputs and preferences; ensure exports include jurisdictional metadata for context without PII.
- Residency interplay
  - Keep export-side checks independent of reasoning semantics; never loosen residency-based controls for performance.

Ops checklist
- Pre-deployment
  - Validate redaction_rules.yml syntax; ensure required keys exist (redact.node_attrs, redact.edge_attrs, pii_tags_blocklist)
  - Run a staging canary to confirm exports contain no PII attributes under default_profile
  - Confirm residency-tagged samples are blocked from disallowed export targets
- Runtime
  - Monitor audit logs for profile usage, dataset identifiers, and redaction version hash
  - Alert on any export where sensitive attributes are detected (automated sampling recommended)
- Post-release
  - Append canary parity summaries automatically to release notes (already configured in CI)
  - Review compliance doc updates and sync with policy owners

Change management and configs
- Configuration files (recommended stubs)
  - config/courts.yaml
  - config/precedent_weights.yaml
  - config/statutory_prefs.yaml
  - config/compliance/redaction_rules.yml
- Versioning
  - Track config versions and include a short hash in audit logs
  - Require approvals for changes to redaction or residency rules

Testing
- Unit tests
  - Redaction: dropping of sensitive attributes, label blocklist, PII tag behavior
  - Residency: inheritance of strictest residency, export blocking behavior
- Integration tests
  - End-to-end doc -> graph -> interpretation -> export with default_profile
  - Audit profile gated and confirmed only in auditor environments
- CI checks
  - Canary remains non-gating but monitored
  - Compliance tests should be gating for production pipelines

Appendix: Minimal redaction_rules.yml stub
redact:
  node_attrs: ["name", "email", "address", "ssn"]
  edge_attrs: ["message_text", "attachment_content"]
  labels_blocklist: ["raw_document_text"]
  pii_tags_blocklist: ["pii_sensitive"]
allowlist:
  node_attrs: ["party_id", "doc_id"]
  labels_allow: ["cites", "same_issue"]

This document defines mandatory controls for production environments. Any deviations require written approval and must be logged and reviewed.