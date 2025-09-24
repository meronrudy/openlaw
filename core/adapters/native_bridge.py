"""
Native Legal Bridge (PyReason-free)

- Assembles graph, rules, and configuration for legal reasoning using the Native engine only.
- No dependency on PyReason; uses core/native/* modules and the NativeLegalFacade.

Usage:
    bridge = NativeLegalBridge(
        reporters_cfg_path="config/normalize/reporters.yml",
        courts_cfg_path="config/normalize/courts.yml",
        burden_cfg_path="config/policy/burden.yml",
        redaction_cfg_path="config/compliance/redaction_rules.yml",
    )
    graph = bridge.load_graphml("path/to/case_graph.graphml", reverse=False)
    facts_node, facts_edge, spec_node_labels, spec_edge_labels = bridge.parse_graph_attributes(
        static_facts=True
    )
    rules = bridge.build_rules_for_claim(
        claim="breach_of_contract",
        jurisdiction="US-CA",
        use_conservative=False
    )
    interp = bridge.run_reasoning(
        graph=graph,
        facts_node=facts_node,
        facts_edge=facts_edge,
        rules=rules,
        tmax=1,
        verbose=False
    )
    results = interp.get_dict()
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
import yaml
import logging
from datetime import datetime
import math

import networkx as nx

from core.native.facade import NativeLegalFacade
from core.native.graph import load_graphml as native_load_graphml, load_graph as native_load_graph, extract_specific_labels
from core.rules_native.native_legal_builder import (
    build_rules_for_claim_native,
    default_clause_weights as _weights_from_courts_cfg,
)
from core.native.rules import NativeRule

logger = logging.getLogger(__name__)


class NativeLegalBridge:
    def __init__(
        self,
        reporters_cfg_path: Optional[str] = None,
        courts_cfg_path: Optional[str] = None,
        burden_cfg_path: Optional[str] = None,
        redaction_cfg_path: Optional[str] = None,
        statutory_prefs_cfg_path: Optional[str] = None,
        precedent_weights_cfg_path: Optional[str] = None,
        privacy_defaults: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize the native legal bridge and load configuration files.

        strict_mode:
          - When True, configuration validation errors raise exceptions (fail fast).
          - When False, validation errors are logged as warnings and defaults are applied.
        """
        self.reporters_cfg = self._load_yaml(reporters_cfg_path)
        self.courts_cfg = self._load_yaml(courts_cfg_path)
        self.burden_cfg = self._load_yaml(burden_cfg_path)
        self.redaction_cfg = self._load_yaml(redaction_cfg_path)
        self.statutory_prefs_cfg = self._load_yaml(statutory_prefs_cfg_path)
        self.precedent_weights_cfg = self._load_yaml(precedent_weights_cfg_path)

        # Validate configurations and optionally fail fast in strict_mode
        self._validate_configs(strict_mode=strict_mode)

        # Privacy defaults placeholders (facade enforces defaults)
        self.atom_trace = not privacy_defaults and False
        self.save_graph_attrs_to_rule_trace = not privacy_defaults and False

        # Last loaded graph (used for attribute parsing)
        self._graph: Optional[nx.DiGraph] = None

        # Cache for specific labels (optional)
        self._specific_node_labels: Optional[Dict[str, List[str]]] = None
        self._specific_edge_labels: Optional[Dict[str, List[Tuple[str, str]]]] = None

        # Legal metadata extracted from the graph (nodes and edges)
        # Nodes: {node_id: {"court": str, "jurisdiction": str, "year": int, "precedential": bool, "statute_refs": List[str], "pii_tags": List[str]}}
        # Edges: [{"u": str, "v": str, "label": str, "treatment": str, "year": int}]
        self._legal_meta_nodes: Optional[Dict[str, Dict[str, Any]]] = None
        self._legal_meta_edges: Optional[List[Dict[str, Any]]] = None

    @staticmethod
    def _load_yaml(path: Optional[str]) -> Dict[str, Any]:
        if not path:
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    # -----------------------
    # Validation helpers
    # -----------------------
    def _validate_configs(self, strict_mode: bool = False) -> None:
        ok = True
        try:
            if self.courts_cfg:
                ok = self._validate_courts_cfg(self.courts_cfg) and ok
            if self.precedent_weights_cfg:
                ok = self._validate_precedent_cfg(self.precedent_weights_cfg) and ok
            if self.statutory_prefs_cfg:
                ok = self._validate_statutory_prefs_cfg(self.statutory_prefs_cfg) and ok
        except Exception as e:
            logger.error("Configuration validation raised an exception: %s", e)
            if strict_mode:
                raise
            ok = False
        if strict_mode and not ok:
            raise ValueError("Configuration validation failed in strict_mode")

    def _validate_courts_cfg(self, cfg: Dict[str, Any]) -> bool:
        good = True
        w = (cfg.get("weights") or {})
        for k in ("controlling", "persuasive", "contrary"):
            if k not in w:
                logger.warning("courts.yaml missing weights.%s; using defaults", k); good = False
            else:
                try:
                    float(w[k])
                except Exception:
                    logger.warning("courts.yaml weights.%s not numeric; using defaults", k); good = False
        hier = cfg.get("hierarchy", {})
        if not isinstance(hier, dict):
            logger.warning("courts.yaml hierarchy must be a mapping"); good = False
        else:
            for j, parents in hier.items():
                if not isinstance(parents, (list, tuple)):
                    logger.warning("courts.yaml hierarchy.%s must be a list", j); good = False
        ro = (cfg.get("rule_overrides") or {})
        if ro and not isinstance(ro, dict):
            logger.warning("courts.yaml rule_overrides must be a mapping"); good = False
        else:
            for j, ov in (ro or {}).items():
                if not isinstance(ov, dict):
                    logger.warning("courts.yaml rule_overrides.%s must be a mapping", j); good = False
                    continue
                for key in ("include_labels", "exclude_labels"):
                    if key in ov and not isinstance(ov[key], (list, tuple)):
                        logger.warning("courts.yaml rule_overrides.%s.%s must be a list", j, key); good = False
        return good

    def _validate_precedent_cfg(self, cfg: Dict[str, Any]) -> bool:
        good = True
        r = (cfg.get("recency") or {})
        try:
            hl = float(r.get("half_life_years", 10)); mm = float(r.get("min_multiplier", 0.5))
            if hl <= 0 or not (0.0 <= mm <= 1.0):
                logger.warning("precedent_weights.yaml recency values out of range"); good = False
        except Exception:
            logger.warning("precedent_weights.yaml recency values invalid"); good = False
        ja = (cfg.get("jurisdiction_alignment") or {})
        for k in ("exact", "ancestor", "sibling", "foreign"):
            try:
                float(ja.get(k, 1.0))
            except Exception:
                logger.warning("precedent_weights.yaml jurisdiction_alignment.%s invalid", k); good = False
        cl = (cfg.get("court_levels") or {})
        if cl and not isinstance(cl, dict):
            logger.warning("precedent_weights.yaml court_levels must be a mapping"); good = False
        tm = (cfg.get("treatment_modifier") or {})
        if tm and not isinstance(tm, dict):
            logger.warning("precedent_weights.yaml treatment_modifier must be a mapping"); good = False
        return good

    def _validate_statutory_prefs_cfg(self, cfg: Dict[str, Any]) -> bool:
        good = True
        allowed = {"textualism", "purposivism", "lenity", ""}
        ds = str(cfg.get("default_style", "") or "")
        if ds not in allowed:
            logger.warning("statutory_prefs.yaml default_style '%s' not in %s", ds, sorted(allowed)); good = False
        ov = (cfg.get("style_overrides") or {})
        if ov and not isinstance(ov, dict):
            logger.warning("statutory_prefs.yaml style_overrides must be a mapping"); good = False
        else:
            for juris, jmap in (ov or {}).items():
                if not isinstance(jmap, dict):
                    logger.warning("statutory_prefs.yaml style_overrides.%s must be a mapping", juris); good = False
                else:
                    for claim, style in jmap.items():
                        if str(style or "") not in allowed and claim != "default":
                            logger.warning("statutory_prefs.yaml style_overrides.%s.%s '%s' not in %s", juris, claim, style, sorted(allowed)); good = False
        return good

    # -----------------------
    # Graph and facts helpers
    # -----------------------
    def load_graphml(self, graphml_path: str, reverse: bool = False) -> nx.DiGraph:
        """
        Load a GraphML into a NetworkX DiGraph (optionally reversed).
        """
        g = native_load_graphml(graphml_path, reverse=reverse)
        self._graph = g
        return g

    def load_graph(self, graph: nx.Graph, reverse: bool = False) -> nx.DiGraph:
        """
        Load a prebuilt NetworkX graph (e.g., from pipeline assembly).
        """
        g = native_load_graph(graph, reverse=reverse)
        self._graph = g
        return g

    def parse_graph_attributes(self, static_facts: bool = True):
        """
        Extract "specific label" mappings from the last loaded graph.
        Returns a 4-tuple for compatibility with PyReason bridge:
          - facts_node: unused by native engine (None)
          - facts_edge: unused by native engine (None)
          - specific_node_labels: dict label -> [node ids]
          - specific_edge_labels: dict label -> [(src, dst)]
        """
        if self._graph is None:
            logger.debug("parse_graph_attributes: no graph loaded; returning empty placeholders")
            self._specific_node_labels = None
            self._specific_edge_labels = None
            self._legal_meta_nodes = None
            self._legal_meta_edges = None
            return None, None, None, None

        try:
            sn, se = extract_specific_labels(self._graph)
            self._specific_node_labels = sn
            self._specific_edge_labels = se
        except Exception as e:
            logger.warning("parse_graph_attributes: specific label extraction failed: %s", e)
            self._specific_node_labels = None
            self._specific_edge_labels = None

        # Extract legal metadata (best-effort; not required by engine)
        try:
            nodes_meta, edges_meta = self._extract_legal_metadata(self._graph)
            self._legal_meta_nodes = nodes_meta
            self._legal_meta_edges = edges_meta
        except Exception as e:
            logger.warning("parse_graph_attributes: legal metadata extraction failed: %s", e)
            self._legal_meta_nodes = None
            self._legal_meta_edges = None

        return None, None, self._specific_node_labels, self._specific_edge_labels
    def get_legal_metadata(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Return last extracted legal metadata: (nodes_meta, edges_meta).
        If extraction was not performed or no graph was loaded, returns ({}, []).
        """
        nodes = self._legal_meta_nodes or {}
        edges = self._legal_meta_edges or []
        return nodes, edges

    # -----------------------
    # Internal helpers
    # -----------------------
    def _extract_legal_metadata(self, graph: nx.DiGraph) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Heuristic extraction of legal metadata from node/edge attributes.
        Nodes: court, jurisdiction, year, precedential, statute_refs, pii_tags
        Edges: u, v, label, treatment, year for common legal labels.
        """
        nodes_meta: Dict[str, Dict[str, Any]] = {}
        for n, attrs in graph.nodes(data=True):
            try:
                d: Dict[str, Any] = {}
                a = attrs or {}
                d["court"] = str(a.get("court", "") or "").strip()
                d["jurisdiction"] = str(a.get("jurisdiction", "") or "").strip()
                y = a.get("year", None)
                try:
                    d["year"] = int(y) if y is not None and str(y).strip() != "" else None
                except Exception:
                    d["year"] = None
                prec = a.get("precedential", False)
                if isinstance(prec, str):
                    prec = prec.strip().lower() in ("true", "yes", "y", "1")
                d["precedential"] = bool(prec)
                stat = a.get("statute_ref", a.get("statute_refs", []))
                if isinstance(stat, str):
                    stat_list = [s.strip() for s in stat.split(",") if s.strip()]
                else:
                    stat_list = [str(s).strip() for s in (stat or [])]
                d["statute_refs"] = stat_list
                pii = a.get("pii_tags", [])
                if isinstance(pii, str):
                    pii_list = [s.strip() for s in pii.split(",") if s.strip()]
                else:
                    pii_list = [str(s).strip() for s in (pii or [])]
                d["pii_tags"] = pii_list
                nodes_meta[str(n)] = d
            except Exception:
                continue

        edges_meta: List[Dict[str, Any]] = []
        for u, v, attrs in graph.edges(data=True):
            try:
                a = attrs or {}
                label_keys = [k for k, val in a.items() if val and str(val).strip().lower() not in ("false", "0", "no", "n")]
                tr = str(a.get("treatment", "") or "").strip()
                yr = a.get("year", None)
                try:
                    yr_i = int(yr) if yr is not None and str(yr).strip() != "" else None
                except Exception:
                    yr_i = None
                for lbl in label_keys:
                    if lbl in ("cites", "same_issue", "controlling_relation", "persuasive_relation", "contrary_to"):
                        edges_meta.append({"u": str(u), "v": str(v), "label": str(lbl), "treatment": tr, "year": yr_i})
            except Exception:
                continue

        return nodes_meta, edges_meta

    def _compute_authority_multipliers(self) -> List[float]:
        """
        Compute clause-class authority multipliers [m_controlling, m_persuasive, m_contrary]
        from extracted legal metadata and precedent_weights config.

        Combines:
        - treatment_modifier[treatment]
        - recency decay using half_life_years and min_multiplier
        - jurisdiction alignment (exact/ancestor/sibling/foreign)
        - court level weights (e.g., US_SCOTUS=1.0, STATE_TRIAL=0.78)
        """
        try:
            edges = self._legal_meta_edges or []
        except Exception:
            edges = []

        nodes = self._legal_meta_nodes or {}

        cfg = self.precedent_weights_cfg if hasattr(self, "precedent_weights_cfg") else {}
        tret = (cfg.get("treatment_modifier", {}) or {})
        recency_cfg = (cfg.get("recency", {}) or {})
        align_cfg = (cfg.get("jurisdiction_alignment", {}) or {})
        level_cfg = (cfg.get("court_levels", {}) or {})

        half_life = float(recency_cfg.get("half_life_years", 10))
        min_mult = float(recency_cfg.get("min_multiplier", 0.5))

        # Current year for recency decay
        try:
            now_year = datetime.utcnow().year
        except Exception:
            now_year = datetime.now().year

        sums = {"controlling": 0.0, "persuasive": 0.0, "contrary": 0.0}

        def _recency(y):
            try:
                age = max(0, int(now_year) - int(y))
                if half_life <= 0:
                    return 1.0
                decay = math.exp(-math.log(2.0) * (age / half_life))
                return max(min_mult, decay)
            except Exception:
                return 1.0

        def _level_weight(court: str) -> float:
            try:
                c = str(court or "").strip()
                return float(level_cfg.get(c, 1.0))
            except Exception:
                return 1.0

        def _alignment(src_j: str, dst_j: str) -> float:
            """
            Determine jurisdictional alignment multiplier for a relation from src_j -> dst_j.
            exact > ancestor > sibling > foreign
            """
            try:
                sj = str(src_j or "").strip()
                dj = str(dst_j or "").strip()
                if not sj or not dj:
                    return float(align_cfg.get("exact", 1.0))
                if sj == dj:
                    return float(align_cfg.get("exact", 1.0))
                # lineage helpers (local import to avoid cycles)
                try:
                    from core.rules_native.native_legal_builder import compute_jurisdiction_lineage  # type: ignore
                    src_line = compute_jurisdiction_lineage(self.courts_cfg or {}, sj)
                    dst_line = compute_jurisdiction_lineage(self.courts_cfg or {}, dj)
                except Exception:
                    src_line, dst_line = [sj], [dj]
                # ancestor if dst in ancestry of src (or vice versa)
                if dj in src_line[1:] or sj in dst_line[1:]:
                    return float(align_cfg.get("ancestor", 0.9))
                # sibling if they share any common ancestor (excluding themselves)
                if set(src_line[1:]).intersection(set(dst_line[1:])):
                    return float(align_cfg.get("sibling", 0.85))
                # foreign otherwise
                return float(align_cfg.get("foreign", 0.75))
            except Exception:
                return 1.0

        for e in edges:
            lbl = str(e.get("label", "") or "").strip()
            treatment = str(e.get("treatment", "") or "").strip().lower()
            year = e.get("year", None)
            u = str(e.get("u", "") or "")
            v = str(e.get("v", "") or "")
            # Node metadata (jurisdiction and court)
            src_meta = nodes.get(u, {}) if isinstance(nodes, dict) else {}
            dst_meta = nodes.get(v, {}) if isinstance(nodes, dict) else {}
            src_juris = str(src_meta.get("jurisdiction", "") or "")
            dst_juris = str(dst_meta.get("jurisdiction", "") or "")
            dst_court = str(dst_meta.get("court", "") or "")

            mult_t = float(tret.get(treatment, 1.0))
            mult_r = _recency(year) if year is not None else 1.0
            mult_align = _alignment(src_juris, dst_juris)
            mult_level = _level_weight(dst_court)

            m = mult_t * mult_r * mult_align * mult_level

            if lbl == "controlling_relation":
                sums["controlling"] += m
            elif lbl == "persuasive_relation":
                sums["persuasive"] += m
            elif lbl == "contrary_to":
                sums["contrary"] += m
            elif lbl == "cites":
                # If only 'cites' provided, treat as persuasive by default
                sums["persuasive"] += m

        m_ctrl = sums["controlling"]
        m_pers = sums["persuasive"]
        m_contra = sums["contrary"]

        # Default to neutral multipliers when no signals present
        if (m_ctrl + m_pers + m_contra) == 0.0:
            return [1.0, 1.0, 1.0]
        return [max(m_ctrl, 1e-9), max(m_pers, 1e-9), max(m_contra, 1e-9)]


    # -----------------------
    # Rules construction
    # -----------------------
    def build_rules_for_claim(
        self,
        claim: str,
        jurisdiction: str = "US-FED",
        use_conservative: bool = False,
        weights: Optional[List[float]] = None,
    ) -> List[NativeRule]:
        """
        Build native rules for a given claim using burden policy. Returns List[NativeRule].

        Notes:
        - If 'weights' is provided explicitly, it overrides the top-level support rule weights.
        - If 'weights' is None, builder-selected weights (including statutory style adjustments) are preserved.
        """
        rules = build_rules_for_claim_native(
            claim=claim,
            jurisdiction=jurisdiction,
            use_conservative=use_conservative,
            courts_cfg=self.courts_cfg,
            burden_cfg=self.burden_cfg,
            statutory_prefs=self.statutory_prefs_cfg,
        )
        # Override weights on the top-level support rule only when provided explicitly
        if weights is not None:
            for r in rules:
                if r.ann_fn and r.target_label.startswith(f"support_for_{claim}"):
                    # Weights length validated by engine during evaluation; ensure length matches if set
                    r.weights = list(weights)
                    break
        else:
            # If no explicit override, apply authority multipliers derived from extracted legal metadata.
            # This adjusts the support rule's clause-class weights in-place while preserving their semantics.
            try:
                mult = self._compute_authority_multipliers()
                if mult and len(mult) == 3:
                    for r in rules:
                        if r.ann_fn and r.target_label.startswith(f"support_for_{claim}") and r.weights and len(r.weights) == 3:
                            scaled = [max(0.0, float(r.weights[i]) * float(mult[i])) for i in range(3)]
                            s = sum(scaled)
                            if s > 0:
                                r.weights = [w / s for w in scaled]
                            break
            except Exception:
                # Non-fatal; leave builder-selected weights unchanged
                pass
        return rules

    # -----------------------
    # Program orchestration
    # -----------------------
    def run_reasoning(
        self,
        graph: nx.DiGraph,
        facts_node,
        facts_edge,
        rules: List[NativeRule],
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ):
        """
        Execute reasoning using the native facade.
        Returns an Interpretation-like object with get_dict().
        """
        # Lazily compute specific label caches (optional for tools/tests)
        try:
            if self._specific_node_labels is None or self._specific_edge_labels is None:
                sn, se = extract_specific_labels(graph)
                self._specific_node_labels = sn
                self._specific_edge_labels = se
        except Exception:
            pass

        facade = NativeLegalFacade(privacy_defaults=True)
        return facade.run_reasoning(
            graph=graph,
            facts_node=facts_node,   # accepted but unused by native engine
            facts_edge=facts_edge,   # accepted but unused by native engine
            rules=rules,
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )

    def export_interpretation(self, interpretation, profile: str = "default_profile"):
        """
        Privacy/export helper:
        - Delegates to Interpretation.export(profile, redaction) when available
        - Constructs redaction dict from self.redaction_cfg (supports top-level and nested 'redact.labels_blocklist')
        """
        try:
            red = self.redaction_cfg or {}
            labels_blocklist = []
            # Support both nested and flat configurations
            if isinstance(red.get("redact"), dict):
                labels_blocklist.extend(red.get("redact", {}).get("labels_blocklist", []) or [])
            labels_blocklist.extend(red.get("labels_blocklist", []) or [])
            # De-duplicate while preserving order
            seen = set()
            dedup = []
            for lbl in labels_blocklist:
                s = str(lbl).strip()
                if s and s not in seen:
                    seen.add(s)
                    dedup.append(s)
            redaction = {"labels_blocklist": dedup}
            if hasattr(interpretation, "export"):
                return interpretation.export(profile=profile, redaction=redaction)
            # Fallback to get_dict() if export() is not available
            return interpretation.get_dict() if hasattr(interpretation, "get_dict") else {}
        except Exception as e:
            logger.warning("export_interpretation: export failed; falling back to get_dict: %s", e)
            return interpretation.get_dict() if hasattr(interpretation, "get_dict") else {}

# -----------------------
# Convenience helpers and metadata accessors
# -----------------------
def weights_from_courts_cfg(courts_cfg: Dict[str, Any]) -> List[float]:
    """
    Returns a [w_controlling, w_persuasive, w_contrary] vector that sums to 1.0.
    """
    return _weights_from_courts_cfg(courts_cfg)


def get_jurisdiction_lineage(courts_cfg: Dict[str, Any], jurisdiction: str) -> List[str]:
    """
    Compute jurisdiction lineage using builder utility for external callers.
    """
    from core.rules_native.native_legal_builder import compute_jurisdiction_lineage  # local import to avoid cycles
    return compute_jurisdiction_lineage(courts_cfg, jurisdiction)

