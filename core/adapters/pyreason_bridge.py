"""
PyReason Legal Bridge
- Assembles facts, rules, and configuration for legal reasoning
- Enforces privacy defaults (atom_trace=False, save_graph_attributes_to_rule_trace=False)
- Orchestrates Program reasoning with legal annotation functions registered

Usage:
    bridge = PyReasonLegalBridge(
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

from typing import Dict, List, Optional, Any
import yaml
import networkx as nx
import logging
import os

# PyReason imports
from pyreason.scripts.program.program import Program
from pyreason.scripts.rules.rule import Rule as PRRule
from pyreason.scripts.utils.graphml_parser import GraphmlParser
import pyreason.scripts.annotation_functions.annotation_functions as ann
import numba
import pyreason.scripts.numba_wrapper.numba_types.label_type as label

# Native facade (for engine selection toggle)
from core.native.facade import NativeLegalFacade

logger = logging.getLogger(__name__)


class PyReasonLegalBridge:
    def __init__(
        self,
        reporters_cfg_path: Optional[str] = None,
        courts_cfg_path: Optional[str] = None,
        burden_cfg_path: Optional[str] = None,
        redaction_cfg_path: Optional[str] = None,
        privacy_defaults: bool = True,
        engine_impl: Optional[str] = None,  # "pyreason" (default) or "native"
    ):
        """
        Initialize the legal bridge and load configuration files.
        """
        self.reporters_cfg = self._load_yaml(reporters_cfg_path)
        self.courts_cfg = self._load_yaml(courts_cfg_path)
        self.burden_cfg = self._load_yaml(burden_cfg_path)
        self.redaction_cfg = self._load_yaml(redaction_cfg_path)

        # Engine selection (env wins over ctor). Default is now "native" per migration plan.
        self.engine_impl = (engine_impl or os.getenv("LEGAL_ENGINE_IMPL", "native")).strip().lower()

        # Privacy defaults as requested:
        # atom_trace=False, save_graph_attributes_to_rule_trace=False
        self.atom_trace = not privacy_defaults and False  # keep False if privacy_defaults=True
        self.save_graph_attrs_to_rule_trace = not privacy_defaults and False

        # Default reasoning flags (aligned with v1 posture)
        self.reverse_graph = False
        self.persistent = True
        self.inconsistency_check = True
        self.store_interpretation_changes = False  # minimize trace surface by default
        self.parallel_computing = False
        self.update_mode = "intersection"  # PyReason default union/intersection semantics
        self.allow_ground_rules = True
        self.fp_version = False

        # Registry of annotation functions by name (must be numba-compatible)
        self.annotation_functions = [
            ann.average,
            ann.maximum,
            ann.minimum,
            ann.legal_burden_civil_051,
            ann.legal_burden_clear_075,
            ann.legal_burden_criminal_090,
            ann.legal_conservative_min,
            ann.precedent_weighted,
        ]

        # GraphML helper
        self._graphml = GraphmlParser()
        self._specific_node_labels = None
        self._specific_edge_labels = None

    @staticmethod
    def _load_yaml(path: Optional[str]) -> Dict[str, Any]:
        if not path:
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    # -----------------------
    # Graph and facts helpers
    # -----------------------
    def load_graphml(self, graphml_path: str, reverse: bool = False) -> nx.DiGraph:
        """
        Load a GraphML into a NetworkX DiGraph (optionally reversed).
        """
        graph = self._graphml.parse_graph(graphml_path, reverse)
        return graph

    def load_graph(self, graph: nx.Graph, reverse: bool = False) -> nx.DiGraph:
        """
        Load a prebuilt NetworkX graph (e.g., from pipeline assembly).
        """
        return self._graphml.load_graph(graph.reverse() if reverse else graph)

    def parse_graph_attributes(self, static_facts: bool = True):
        """
        From the loaded graph, extract graph attribute facts and specific label mappings.
        Returns:
          - facts_node: numba typed list of node facts
          - facts_edge: numba typed list of edge facts
          - specific_node_labels: numba typed dict of label -> [node ids]
          - specific_edge_labels: numba typed dict of label -> [(src, dst)]
        """
        facts_node, facts_edge, specific_node_labels, specific_edge_labels = (
            self._graphml.parse_graph_attributes(static_facts)
        )
        # Cache for Program.reason() setup
        self._specific_node_labels = specific_node_labels
        self._specific_edge_labels = specific_edge_labels
        return facts_node, facts_edge, specific_node_labels, specific_edge_labels

    # -----------------------
    # Rules construction
    # -----------------------
    def build_rules_for_claim(
        self,
        claim: str,
        jurisdiction: str = "US-FED",
        use_conservative: bool = False,
        weights: Optional[List[float]] = None,
    ) -> List[PRRule]:
        """
        Build support rule and derivation rules for a given claim using burden policy.
        Returns a list of PRRule instances ready for Program.
        """
        from core.rules.legal_rules import (
            map_burden_to_fn_name,
            default_clause_weights,
            build_derivation_rules,
            build_support_rule,
        )

        burden_fn = map_burden_to_fn_name(claim, jurisdiction, self.burden_cfg)
        if use_conservative:
            # Override to conservative aggregator if requested
            burden_fn = "legal_conservative_min"

        if weights is None:
            weights = default_clause_weights(self.courts_cfg)

        rules: List[PRRule] = []
        # Support rule for the claim
        support_rule = build_support_rule(claim=claim, ann_fn_name=burden_fn, weights=weights)
        rules.append(support_rule)

        # Derivation rules (controlling/persuasive/contrary)
        rules.extend(build_derivation_rules())

        return rules

    # -----------------------
    # Program orchestration
    # -----------------------
    def _empty_ipl(self):
        """
        Build an empty numba-typed IPL structure.
        """
        ipl = numba.typed.List.empty_list(
            numba.types.Tuple((label.label_type, label.label_type))
        )
        return ipl

    def _instantiate_program(
        self,
        graph: nx.DiGraph,
        facts_node,
        facts_edge,
        rules: List[PRRule],
    ) -> Program:
        """
        Create Program with privacy defaults and annotation registry.
        """
        ipl = self._empty_ipl()

        prog = Program(
            graph,
            facts_node,
            facts_edge,
            rules,
            ipl,
            self.annotation_functions,
            self.reverse_graph,
            self.atom_trace,
            self.save_graph_attrs_to_rule_trace,
            self.persistent,
            self.inconsistency_check,
            self.store_interpretation_changes,
            self.parallel_computing,
            self.update_mode,
            self.allow_ground_rules,
            self.fp_version,
        )

        # Provide specific labels parsed from GraphML (if any) to Interpretation
        if self._specific_node_labels is not None:
            Program.specific_node_labels = self._specific_node_labels
        if self._specific_edge_labels is not None:
            Program.specific_edge_labels = self._specific_edge_labels

        return prog

    def run_reasoning(
        self,
        graph: nx.DiGraph,
        facts_node,
        facts_edge,
        rules: List[PRRule],
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ):
        """
        Execute reasoning with engine selection:
         - "pyreason" (default): run PyReason Program
         - "native": run core.native FixedPointEngine via NativeLegalFacade
        Returns an Interpretation-like object with get_dict().
        """
        # Resolve engine selection at call time (env override). Default native.
        engine_impl = os.getenv("LEGAL_ENGINE_IMPL", self.engine_impl or "native").strip().lower()

        if engine_impl == "native":
            logger.warning("Native engine selected. Set LEGAL_ENGINE_IMPL=pyreason to temporarily revert during migration.")
            facade = NativeLegalFacade(privacy_defaults=True)
            return facade.run_reasoning(
                graph=graph,
                facts_node=facts_node,
                facts_edge=facts_edge,
                rules=rules,
                tmax=tmax,
                convergence_threshold=convergence_threshold,
                convergence_bound_threshold=convergence_bound_threshold,
                verbose=verbose,
            )

        # Fallback to PyReason engine
        prog = self._instantiate_program(graph, facts_node, facts_edge, rules)
        interp = prog.reason(
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )
        return interp


# -----------------------
# Convenience helpers
# -----------------------
def weights_from_courts_cfg(courts_cfg: Dict[str, Any]) -> List[float]:
    """
    Optional external helper to derive clause weights from courts config.
    Returns a [w_controlling, w_persuasive, w_contrary] vector that sums to 1.0.
    """
    # Simple defaults; callers can override
    controlling_weight = float(courts_cfg.get("weights", {}).get("controlling", 0.6))
    persuasive_weight = float(courts_cfg.get("weights", {}).get("persuasive", 0.3))
    contrary_weight = float(courts_cfg.get("weights", {}).get("contrary", 0.1))

    total = max(controlling_weight + persuasive_weight + contrary_weight, 1e-9)
    controlling_weight /= total
    persuasive_weight /= total
    contrary_weight /= total
    return [controlling_weight, persuasive_weight, contrary_weight]