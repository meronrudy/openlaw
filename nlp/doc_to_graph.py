"""
Document-to-Graph converter for legal reasoning pipelines.

- Extracts citations and basic entities from raw text (using LegalNERPipeline and CitationExtractor)
- Builds a NetworkX DiGraph ready for ingestion by the Native bridge
- Attaches legal-relevant attributes:
  - Nodes: court (opt), jurisdiction (opt), year (opt), precedential (opt), statute_refs, pii_tags
  - Edges: cites(u,v), same_issue(u,v) (placeholder), controlling_relation/persuasive_relation (optional), treatment, year

Usage:
  from nlp.doc_to_graph import doc_to_graph, write_graphml
  g = doc_to_graph(text)
  write_graphml(g, "examples/graphs/generated_case.graphml")
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import re

try:
    import networkx as nx  # type: ignore
except Exception:  # pragma: no cover
    nx = None


def _safe_nx():
    if nx is None:
        raise RuntimeError("networkx is required for doc_to_graph; please install networkx")
    return nx


def _normalize_case_id(plaintiff: str, defendant: str, year: Optional[str]) -> str:
    p = re.sub(r"\s+", "_", (plaintiff or "").strip())
    d = re.sub(r"\s+", "_", (defendant or "").strip())
    y = (str(year).strip() if year else "")
    return f"case::{p}_v_{d}{('_' + y) if y else ''}"


def _normalize_statute_id(title: str, section: str) -> str:
    t = str(title).strip()
    s = str(section).strip()
    return f"statute::{t}_USC_{s}"


def _extract_from_citations(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (cases, statutes) from raw text using lightweight patterns.

    For production, prefer nlp.CitationExtractor which is richer.
    Here we implement minimal built-ins to keep this module standalone.
    """
    cases: List[Dict[str, Any]] = []
    statutes: List[Dict[str, Any]] = []

    # Case: "Plaintiff v. Defendant, 347 U.S. 483 (1954)" or "Plaintiff v. Defendant"
    case_pat = re.compile(
        r"([A-Z][\w\s&\.]+)\s+v\.?\s+([A-Z][\w\s&\.]+)(?:,?\s+(\d+)\s+[A-Z][\w\.]+\s+\d+)?(?:\s+\((\d{4})\))?",
        re.IGNORECASE,
    )
    for m in case_pat.finditer(text):
        cases.append(
            {
                "plaintiff": m.group(1).strip(),
                "defendant": m.group(2).strip(),
                "volume": m.group(3),
                "year": m.group(4),
            }
        )

    # Statute: "42 U.S.C. § 1981" | "42 USC 1981" (with subsections)
    stat_pat1 = re.compile(r"(\d+)\s+U\.?S\.?C\.?\s*§?\s*(\d+(?:\([a-z0-9]+\))*)", re.IGNORECASE)
    stat_pat2 = re.compile(r"(\d+)\s+USC\s*§?\s*(\d+(?:\([a-z0-9]+\))*)", re.IGNORECASE)
    for m in stat_pat1.finditer(text):
        statutes.append({"title": m.group(1), "section": m.group(2)})
    for m in stat_pat2.finditer(text):
        statutes.append({"title": m.group(1), "section": m.group(2)})

    return cases, statutes


def _extract_pii_entities(text: str) -> List[Tuple[str, Tuple[int, int]]]:
    """
    Very lightweight PERSON-like matcher to demonstrate PII tagging.
    In production use nlp.LegalNERPipeline.
    """
    person_pat = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
    out = []
    for m in person_pat.finditer(text):
        # Skip obvious citations like "X v. Y"
        if " v " in m.group().lower() or " v. " in m.group().lower():
            continue
        out.append((m.group(), m.span()))
    return out


def doc_to_graph(
    text: str,
    jurisdiction: str = "US-CA",
    default_year: Optional[int] = None,
    assume_persuasive: bool = True,
) -> Any:
    """
    Convert text into a legal graph suitable for the Native engine.

    Nodes (examples):
      - case::<plaintiff>_v_<defendant>[_<year>]
      - statute::<title>_USC_<section>

    Edges:
      - cites(case_u, case_v) where case_u cites case_v (heuristic; we connect all cases to statutes they mention)
      - persuasive_relation(case_u, case_v) if assume_persuasive True
    """
    _ = _safe_nx()
    G = nx.DiGraph()

    # Extract citations and statutes
    cases, statutes = _extract_from_citations(text)

    # Create statute nodes
    for st in statutes:
        sid = _normalize_statute_id(st.get("title", ""), st.get("section", ""))
        if not G.has_node(sid):
            G.add_node(
                sid,
                statute_ref=f"{st.get('title')} U.S.C. § {st.get('section')}",
                jurisdiction=jurisdiction,
                statute_refs=[f"{st.get('title')} U.S.C. § {st.get('section')}"],
            )

    # Create case nodes
    case_ids: List[str] = []
    for cs in cases:
        cid = _normalize_case_id(cs.get("plaintiff", ""), cs.get("defendant", ""), cs.get("year", None))
        if not G.has_node(cid):
            try:
                year_val = int(cs["year"]) if cs.get("year") else (int(default_year) if default_year else None)
            except Exception:
                year_val = None
            G.add_node(
                cid,
                court="",  # unknown from plain text, reserved for pipeline normalization
                jurisdiction=jurisdiction,
                year=year_val,
                precedential=True,  # default assumption; can be refined
                statute_refs=[],
            )
        case_ids.append(cid)

    # Add basic edges: connect each case to statutes mentioned (cites)
    for cid in case_ids:
        for st in statutes:
            sid = _normalize_statute_id(st.get("title", ""), st.get("section", ""))
            if G.has_node(sid) and not G.has_edge(cid, sid):
                G.add_edge(cid, sid, cites=True, treatment="neutral", year=G.nodes[cid].get("year"))

    # Optional persuasive relations among cases (dense heuristic)
    if assume_persuasive and len(case_ids) > 1:
        src = case_ids[0]
        for tgt in case_ids[1:]:
            if not G.has_edge(src, tgt):
                G.add_edge(src, tgt, persuasive_relation=True, treatment="neutral", year=G.nodes[src].get("year"))

    # PII tagging: mark PERSON entities from simple regex as pii_basic on the "document" node
    doc_node = f"doc::{jurisdiction}"
    if not G.has_node(doc_node):
        G.add_node(doc_node, pii_tags=["pii_basic"], statute_refs=[])
    for ent, _span in _extract_pii_entities(text):
        # Accumulate PII signal in doc node
        tags = set(G.nodes[doc_node].get("pii_tags", []) or [])
        tags.add("pii_basic")
        G.nodes[doc_node]["pii_tags"] = sorted(tags)

    return G


def write_graphml(graph: Any, path: str) -> None:
    _ = _safe_nx()
    nx.write_graphml(graph, path)

def doc_to_graph_auto(
    text: str,
    jurisdiction: str = "US-CA",
    default_year: Optional[int] = None,
    assume_persuasive: bool = True,
) -> Any:
    """
    Auto pipeline: build a graph from text, preferring NLP-based extraction if available,
    and falling back to regex-only doc_to_graph otherwise.

    - If nlp.LegalNERPipeline and nlp.CitationExtractor are importable, use them to enrich nodes/edges.
    - Always returns a NetworkX DiGraph suitable for NativeLegalBridge.load_graph(...).
    """
    G = doc_to_graph(
        text=text,
        jurisdiction=jurisdiction,
        default_year=default_year,
        assume_persuasive=assume_persuasive,
    )

    # Try to enrich using NLP pipeline (optional dependency)
    try:
        from nlp.legal_ner import LegalNERPipeline, CitationExtractor  # type: ignore

        ner = LegalNERPipeline()
        citx = CitationExtractor()

        # Extract citations
        citations = citx.extract_citations(text)
        cases = []
        statutes = []
        for c in citations:
            parsed = citx.parse_citation_components(c)
            norm = citx.normalize_citation(c)
            if c.get("type") == "case":
                cases.append(
                    {
                        "plaintiff": parsed.get("plaintiff"),
                        "defendant": parsed.get("defendant"),
                        "year": parsed.get("year"),
                        "normalized": norm.get("standard_form"),
                    }
                )
            elif c.get("type") == "statute":
                statutes.append(
                    {
                        "title": parsed.get("title"),
                        "section": parsed.get("section"),
                        "normalized": norm.get("standard_form"),
                    }
                )

        # Update/add nodes using normalized citations
        for cs in cases:
            cid = _normalize_case_id(cs.get("plaintiff", ""), cs.get("defendant", ""), cs.get("year", None))
            if not G.has_node(cid):
                try:
                    year_val = int(cs["year"]) if cs.get("year") else (int(default_year) if default_year else None)
                except Exception:
                    year_val = None
                G.add_node(
                    cid,
                    court="",
                    jurisdiction=jurisdiction,
                    year=year_val,
                    precedential=True,
                    statute_refs=[],
                )
        for st in statutes:
            sid = _normalize_statute_id(st.get("title", ""), st.get("section", ""))
            if not G.has_node(sid):
                G.add_node(
                    sid,
                    statute_ref=st.get("normalized") or f"{st.get('title')} U.S.C. § {st.get('section')}",
                    jurisdiction=jurisdiction,
                    statute_refs=[st.get("normalized")] if st.get("normalized") else [],
                )

        # Connect NLP-detected relations (conservative: treat as cites)
        for cs in cases:
            cid = _normalize_case_id(cs.get("plaintiff", ""), cs.get("defendant", ""), cs.get("year", None))
            for st in statutes:
                sid = _normalize_statute_id(st.get("title", ""), st.get("section", ""))
                if G.has_node(cid) and G.has_node(sid) and not G.has_edge(cid, sid):
                    G.add_edge(cid, sid, cites=True, treatment="neutral", year=G.nodes[cid].get("year"))

        # Optional persuasive relations among NLP-detected cases (dense heuristic)
        if assume_persuasive and len(cases) > 1:
            src = _normalize_case_id(cases[0].get("plaintiff", ""), cases[0].get("defendant", ""), cases[0].get("year", None))
            for cs2 in cases[1:]:
                tgt = _normalize_case_id(cs2.get("plaintiff", ""), cs2.get("defendant", ""), cs2.get("year", None))
                if G.has_node(src) and G.has_node(tgt) and not G.has_edge(src, tgt):
                    G.add_edge(src, tgt, persuasive_relation=True, treatment="neutral", year=G.nodes[src].get("year"))

        # PII enrichment via NER (mocked pipeline returns basic PERSON-like spans)
        ents = ner.extract_legal_entities(text)
        pii_tags = set()
        for e in ents:
            if e.get("entity_group") in ("PERSON",):
                pii_tags.add("pii_basic")
        if pii_tags:
            doc_node = f"doc::{jurisdiction}"
            if not G.has_node(doc_node):
                G.add_node(doc_node, pii_tags=sorted(pii_tags), statute_refs=[])
            else:
                tags = set(G.nodes[doc_node].get("pii_tags", []) or [])
                G.nodes[doc_node]["pii_tags"] = sorted(tags.union(pii_tags))

    except Exception:
        # NLP not available; return regex-only graph
        return G

    return G