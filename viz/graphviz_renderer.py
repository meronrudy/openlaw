"""
Graphviz rendering for OpenLaw analysis results (minimal static PNG).

Design goals:
- Minimal footprint: PNG only, no tooltips, no interactivity.
- Saved next to the input document by default.
- Future-friendly: data-driven structure so we can later emit JSON suitable for a JSON->HTML tree viewer.

Input shape (matches CLI "analysis" dict returned by plugin):
{
  "entities": [ { "text", "type", "confidence", "metadata": {...} }, ... ],
  "citations": [ { "text", "type", "confidence", "metadata": {...} }, ... ],
  "original_facts": [ { "statement": "...", ... }, ... ],
  "derived_facts": [ { "statement": "...", "derived_from": [...], "rule_authority": "..." }, ... ],
  "conclusions": [ { "type": "...", "conclusion": "...", "legal_basis": "...", "confidence": 0.xx }, ... ],
  "provenance": {...}  # Optional in many flows; the minimal renderer does not depend on it
}

Output:
- Returns absolute path to generated PNG.

Dependencies:
- python-graphviz (Python package)
- Graphviz system binary ("dot") must be installed and on PATH.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import os

try:
    from graphviz import Digraph
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "graphviz Python package is required. Install with `pip install graphviz`. "
        "Also ensure Graphviz binaries are installed (e.g., `brew install graphviz` on macOS)."
    ) from e


def _safe_label(text: str, max_len: int = 80) -> str:
    """Truncate long labels for readability."""
    if text is None:
        return ""
    t = str(text).strip()
    return (t[: max_len - 1] + "…") if len(t) > max_len else t


def visualize_analysis(
    analysis: Dict[str, Any],
    source_document_path: Optional[str] = None,
    out_path: Optional[str] = None,
    filename_prefix: Optional[str] = None,
    format: str = "png",
) -> str:
    """
    Render a simple, clustered graph of the analysis results.

    - Entities, Facts, Derived Facts, Conclusions, Citations in clusters
    - Edges:
        original_facts  -> derived_facts
        derived_facts   -> conclusions
        citations       -> conclusions (authority reference)
    - Saved as PNG next to the input document by default.

    Args:
        analysis: The analysis results dictionary.
        source_document_path: Path to the source text file (used to determine default output location).
        out_path: Optional explicit output directory. If None, defaults near the document.
        filename_prefix: Optional filename prefix; defaults to stem of source_document_path or "openlaw_viz".
        format: Output format (PNG preferred per minimal spec).

    Returns:
        Absolute path to the generated image file (e.g., ".../document.openlaw.png").
    """
    # Determine output directory and filename
    src = Path(source_document_path) if source_document_path else None
    if out_path:
        out_dir = Path(out_path)
    elif src:
        out_dir = src.parent
    else:
        out_dir = Path.cwd()

    out_dir.mkdir(parents=True, exist_ok=True)

    base_prefix = (
        filename_prefix
        if filename_prefix
        else (src.stem if src else "openlaw_viz")
    )
    file_base = f"{base_prefix}.openlaw"

    dot = Digraph(
        name="OpenLawAnalysis",
        comment="Minimal visualization of OpenLaw analysis results",
        format=format,
        graph_attr={"rankdir": "LR", "splines": "true", "concentrate": "true"},
        node_attr={"shape": "box", "style": "rounded,filled", "color": "#4B5563", "fillcolor": "#E5E7EB"},
        edge_attr={"color": "#6B7280"},
    )

    # Clusters
    with dot.subgraph(name="cluster_entities") as c:
        c.attr(label="Entities", color="#9CA3AF")
        entities = analysis.get("entities", []) or []
        for idx, ent in enumerate(entities, start=1):
            node_id = f"ENT_{idx}"
            label = f"{_safe_label(ent.get('type', 'ENTITY'))}\n{_safe_label(ent.get('text', ''))}"
            c.node(node_id, label=label, fillcolor="#DBEAFE")  # light blue

    with dot.subgraph(name="cluster_original_facts") as c:
        c.attr(label="Original Facts", color="#9CA3AF")
        original_facts = analysis.get("original_facts", []) or []
        for idx, fact in enumerate(original_facts, start=1):
            node_id = f"OF_{idx}"
            label = f"{_safe_label(fact.get('statement', 'FACT'))}"
            c.node(node_id, label=label, fillcolor="#FDE68A")  # yellow

    with dot.subgraph(name="cluster_derived_facts") as c:
        c.attr(label="Derived Facts", color="#9CA3AF")
        derived_facts = analysis.get("derived_facts", []) or []
        for idx, df in enumerate(derived_facts, start=1):
            node_id = f"DF_{idx}"
            rule = df.get("rule_authority", "")
            label = f"{_safe_label(df.get('statement', 'DERIVED'))}\n{_safe_label(rule)}"
            c.node(node_id, label=label, fillcolor="#C7F9CC")  # green

    with dot.subgraph(name="cluster_conclusions") as c:
        c.attr(label="Conclusions", color="#9CA3AF")
        conclusions = analysis.get("conclusions", []) or []
        for idx, con in enumerate(conclusions, start=1):
            node_id = f"CONC_{idx}"
            label = f"{_safe_label(con.get('type', 'CONCLUSION'))}\n{_safe_label(con.get('conclusion', ''))}\n{_safe_label(con.get('legal_basis', ''))}"
            c.node(node_id, label=label, fillcolor="#FBCFE8")  # pink

    with dot.subgraph(name="cluster_citations") as c:
        c.attr(label="Citations", color="#9CA3AF")
        citations = analysis.get("citations", []) or []
        for idx, cit in enumerate(citations, start=1):
            node_id = f"CIT_{idx}"
            label = f"{_safe_label(cit.get('text', 'CITATION'))}"
            c.node(node_id, label=label, fillcolor="#E5E7EB")

    # Build lookup for referencing nodes by statement/value
    # Map: statement string -> DF_n / OF_n
    of_map = { (fact.get("statement") or f"OF_{i}"): f"OF_{i}" for i, fact in enumerate(original_facts, start=1) }
    df_map = { (df.get("statement") or f"DF_{i}"): f"DF_{i}" for i, df in enumerate(derived_facts, start=1) }

    # Edges: original_facts -> derived_facts (via derived_from)
    for idx, df in enumerate(derived_facts, start=1):
        df_id = f"DF_{idx}"
        for prem in df.get("derived_from", []) or []:
            # If premise matches an original fact statement, link OF -> DF
            src_id = of_map.get(prem) or df_map.get(prem)
            if src_id:
                dot.edge(src_id, df_id)

    # Edges: derived_facts -> conclusions (simple link on order)
    for idx, con in enumerate(conclusions, start=1):
        conc_id = f"CONC_{idx}"
        # Heuristic: link all derived facts to each conclusion (or refine later)
        for j in range(len(derived_facts)):
            dot.edge(f"DF_{j+1}", conc_id)

    # Edges: citations -> conclusions (authority ref)
    for idx, cit in enumerate(citations, start=1):
        cit_id = f"CIT_{idx}"
        for j in range(len(conclusions)):
            dot.edge(cit_id, f"CONC_{j+1}")

    # Render to disk
    dst = out_dir / file_base
    filepath = dot.render(filename=str(dst), cleanup=True)
    # graphviz renders with extension automatically (e.g., .png)
    # Ensure absolute path is returned
    return str(Path(filepath).resolve())