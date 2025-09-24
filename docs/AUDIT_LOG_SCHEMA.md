# Audit Log Schema (Append-only, Hash-chained)

This document specifies a portable, append-only, hash-chained log format for governance and evidence. It is agnostic to the backing store (filesystem, S3, database). The recommended encoding is JSON Lines (JSONL), one event per line.

Goals
- Tamper-evident: Each record includes the hash of the previous record (prev_hash).
- Verifiable: A full log replay re-computes the chain to confirm integrity.
- Portable: Minimal schema; text-friendly (JSONL) for ingestion/export.
- Flexible: Extensible via metadata field.

Record fields (JSON)
- version: integer. Schema version (1).
- event_id: string (UUIDv4 recommended). Unique identifier of the event.
- ts: string (ISO 8601). Event timestamp in UTC.
- actor:
  - id: string. Service or user principal.
  - type: string. One of [system, user, service].
- action: string. Ex: ingest_document, redact_detected, build_rules, run_reasoning, export_results, benchmark_run.
- resource:
  - type: string. Ex: document, graph, config, model, benchmark.
  - id: string. Resource identifier (e.g., doc hash, graph id).
  - path: string (optional). Relative path in the repository or storage bucket.
- inputs: object. Input parameters, truncated/scrubbed for PII (after redaction).
- outputs: object. Summary outputs only; never raw PII.
- outcome: string. One of [success, failure, partial].
- prev_hash: string (hex). Hash of previous record in the chain or "0" for the first record.
- hash: string (hex). Hash of the current record with prev_hash applied.
- signature: string (optional). Detached signature over hash (HSM-backed recommended).
- metadata: object (optional). Extensible metadata (e.g., jurisdiction, claim, tmax, versions).

Hashing
- Compute hash over the canonicalized JSON (e.g., sorted keys, UTF-8) excluding the hash and signature fields.
- Use SHA-256 as default.

Example JSONL entry
{"version":1,"event_id":"a8a5f9c8-1e81-4a9a-9f9d-8d01a1e0b3f9","ts":"2025-09-18T14:40:00Z","actor":{"id":"batch_ingest","type":"service"},"action":"ingest_document","resource":{"type":"document","id":"doc_4b5e...","path":"ingest/2025-09-18/doc1.pdf"},"inputs":{"checksum":"1b2m2y8as...","content_type":"application/pdf"},"outputs":{"pages":12},"outcome":"success","prev_hash":"0","hash":"3e5f07a2...","metadata":{"pipeline_version":"1.0.0"}}
{"version":1,"event_id":"d4f3c5b6-935c-4aab-86d6-4f255a9b1fb5","ts":"2025-09-18T14:41:12Z","actor":{"id":"redactor","type":"service"},"action":"redact_detected","resource":{"type":"document","id":"doc_4b5e..."},"inputs":{"ruleset":"config/compliance/redaction_rules.yml"},"outputs":{"matches":3,"blocked":false},"outcome":"success","prev_hash":"3e5f07a2...","hash":"a41b8e9d...","metadata":{"sample_before_after":false}}

Operational guidance
- Store JSONL files in date-partitioned directories: logs/audit/YYYY/MM/DD/app.log.jsonl
- Rotate logs daily; keep file sizes manageable (< 100MB).
- Sign each record (signature field) or sign end-of-day manifest with Merkle root.
- For export, bundle:
  - The JSONL files
  - Hash chain report (computed)
  - Optional signatures (PGP, X.509)
- For verification:
  - Recompute the chain and compare the final hash to recorded value(s).
  - Verify signatures using public keys.

PII considerations
- inputs and outputs must be redacted; never include raw PII. Use placeholders and/or masked values.
- Ensure redaction rules (config/compliance/redaction_rules.yml) are applied pre-persistence.

Minimal Python reference (hash computation)
```python
import hashlib, json

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def compute_hash(record):
    data = dict(record)
    data.pop("hash", None)
    data.pop("signature", None)
    return hashlib.sha256(canonical(data)).hexdigest()
```

Integration hints
- Emit one audit line for each major stage: ingest → redact → normalize → graph build → rule build → reasoning → export → benchmark.
- Use separate channels/loggers for security-sensitive and general operations; merge only scrubbed data into the audit log.