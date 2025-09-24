#!/usr/bin/env python3
"""
Document-to-Graph Ingestion CLI

Converts a raw legal text document into a NetworkX DiGraph encoded as GraphML,
ready for ingestion by the Native Legal Bridge and rule engine.

- Auto mode uses NLP components if available: nlp.LegalNERPipeline and nlp.CitationExtractor
- Regex mode uses lightweight built-ins only (no external NLP dependency)
- Outputs GraphML with nodes/edges carrying legal-relevant attributes

Usage examples:
  # Auto mode with defaults (reads from stdin)
  cat ./examples/legal/opinion.txt | python -m scripts.ingest.doc_to_graph_cli -o examples/graphs/generated_case.graphml

  # Regex-only mode from a file
  python -m scripts.ingest.doc_to_graph_cli ./examples/legal/opinion.txt -o examples/graphs/generated_case.graphml --mode regex

  # Specify jurisdiction and year, disable persuasive case-to-case links
  python -m scripts.ingest.doc_to_graph_cli ./examples/legal/opinion.txt -o ./out.graphml --jurisdiction US-CA --default-year 2020 --no-assume-persuasive --summary
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

try:
    from nlp.doc_to_graph import doc_to_graph, doc_to_graph_auto, write_graphml  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[doc_to_graph_cli] Failed to import pipeline: {e}", file=sys.stderr)
    sys.exit(2)


def _read_text(path: str) -> str:
    if path == "-" or path.strip() == "":
        return sys.stdin.read()
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return p.read_text(encoding="utf-8", errors="ignore")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Convert legal document text to GraphML for native legal reasoning.")
    p.add_argument("input", nargs="?", default="-", help="Path to input text file, or '-' for stdin (default: '-')")
    p.add_argument("-o", "--output", required=True, help="Output GraphML path")
    p.add_argument("--jurisdiction", default="US-CA", help="Jurisdiction code for node defaults (default: US-CA)")
    p.add_argument("--default-year", type=int, default=None, help="Default year to use when case year is missing")
    p.add_argument("--assume-persuasive", dest="assume_persuasive", action="store_true", default=True,
                   help="Create persuasive case-to-case edges heuristically (default: enabled)")
    p.add_argument("--no-assume-persuasive", dest="assume_persuasive", action="store_false",
                   help="Disable persuasive case-to-case edges")
    p.add_argument("--mode", choices=("auto", "regex"), default="auto",
                   help="Extraction mode: 'auto' (NER + citations if available) or 'regex' only (default: auto)")
    p.add_argument("--summary", action="store_true", help="Print a summary (nodes/edges) after writing GraphML")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_text(args.input)
    except Exception as e:
        print(f"[doc_to_graph_cli] Error reading input: {e}", file=sys.stderr)
        return 2

    try:
        if args.mode == "auto":
            G = doc_to_graph_auto(
                text=text,
                jurisdiction=args.jurisdiction,
                default_year=args.default_year,
                assume_persuasive=args.assume_persuasive,
            )
        else:
            G = doc_to_graph(
                text=text,
                jurisdiction=args.jurisdiction,
                default_year=args.default_year,
                assume_persuasive=args.assume_persuasive,
            )
    except Exception as e:
        print(f"[doc_to_graph_cli] Error building graph: {e}", file=sys.stderr)
        return 3

    try:
        write_graphml(G, args.output)
    except Exception as e:
        print(f"[doc_to_graph_cli] Error writing GraphML: {e}", file=sys.stderr)
        return 4

    if args.summary:
        try:
            n = G.number_of_nodes()
            m = G.number_of_edges()
            print(f"[doc_to_graph_cli] Wrote {args.output}  nodes={n}  edges={m}")
        except Exception:
            print(f"[doc_to_graph_cli] Wrote {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())