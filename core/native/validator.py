"""
Native vs PyReason Parity Validator (Exact Equality)

Runs both engines side-by-side on the same inputs and verifies:
- Derived fact keys match exactly
- Probability interval bounds match exactly

Usage (programmatic):
    from core.native.validator import DualEngineValidator
    report = DualEngineValidator().validate_graphml(
        graphml_path="examples/legal/min_case_graph.graphml",
        claim="breach_of_contract",
        jurisdiction="US-CA",
        reporters_cfg_path="config/normalize/reporters.yml",
        courts_cfg_path="config/normalize/courts.yml",
        burden_cfg_path="config/policy/burden.yml",
        redaction_cfg_path="config/compliance/redaction_rules.yml",
        tmax=1,
        verbose=False,
    )
    assert report["match"], report

This module depends on the existing bridge to obtain a PyReason interpretation,
and uses the core.native.facade.NativeLegalFacade for the Native interpretation.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

# Bridge (PyReason) and Native facade
# Import PyReason bridge lazily/optionally to avoid hard dependency at import time
try:
    from core.adapters.pyreason_bridge import PyReasonLegalBridge  # type: ignore
except Exception:
    PyReasonLegalBridge = None  # type: ignore

from core.native.facade import (
    NativeLegalFacade,
    ExactEqualityValidator,
    wrap_pyreason_interpretation,
    NativeInterpretation,
)


class DualEngineValidator:
    """
    Orchestrates dual-run of PyReason and Native engines and validates exact equality.
    """

    def __init__(self) -> None:
        self._exact = ExactEqualityValidator()

    def validate_graphml(
        self,
        graphml_path: str,
        claim: str,
        jurisdiction: str = "US-FED",
        reporters_cfg_path: Optional[str] = "config/normalize/reporters.yml",
        courts_cfg_path: Optional[str] = "config/normalize/courts.yml",
        burden_cfg_path: Optional[str] = "config/policy/burden.yml",
        redaction_cfg_path: Optional[str] = "config/compliance/redaction_rules.yml",
        use_conservative: bool = False,
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Load a GraphML once, build rules/inputs, and run both engines; then compare.
        Returns a report dict: {"match": bool, ...details...}
        """
        # 1) Build PyReason inputs via bridge
        if PyReasonLegalBridge is None:
            return {
                "match": False,
                "reason": "pyreason_unavailable",
            }
        bridge = PyReasonLegalBridge(
            reporters_cfg_path=reporters_cfg_path,
            courts_cfg_path=courts_cfg_path,
            burden_cfg_path=burden_cfg_path,
            redaction_cfg_path=redaction_cfg_path,
            privacy_defaults=True,
        )
        graph = bridge.load_graphml(graphml_path, reverse=False)
        facts_node, facts_edge, spec_node_labels, spec_edge_labels = bridge.parse_graph_attributes(
            static_facts=True
        )
        pr_rules = bridge.build_rules_for_claim(
            claim=claim,
            jurisdiction=jurisdiction,
            use_conservative=use_conservative,
        )

        # 2) Run PyReason
        pr_interp = bridge.run_reasoning(
            graph=graph,
            facts_node=facts_node,
            facts_edge=facts_edge,
            rules=pr_rules,
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )

        # 3) Run Native with API-compatible call
        native = NativeLegalFacade(privacy_defaults=True)
        nat_interp = native.run_reasoning(
            graph=graph,
            facts_node=facts_node,
            facts_edge=facts_edge,
            rules=pr_rules,
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )

        # 4) Convert PR to native-format interpretation and compare
        pr_wrapped: NativeInterpretation = wrap_pyreason_interpretation(pr_interp)
        report = self._exact.validate(pr_wrapped, nat_interp)
        return report

    def validate_from_objects(
        self,
        graph: Any,
        facts_node: Any,
        facts_edge: Any,
        rules: List[Any],
        tmax: int = 1,
        convergence_threshold: float = -1,
        convergence_bound_threshold: float = -1,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate using prebuilt inputs (bypassing GraphML ingestion).
        """
        # PyReason path via bridge-like Program is not available here,
        # so this method expects 'rules' to be consumable by both engines upstream.
        # For now, this method focuses on the Native path only and returns a mismatch
        # report placeholder until a PyReason runner is injected.
        native = NativeLegalFacade(privacy_defaults=True)
        nat_interp = native.run_reasoning(
            graph=graph,
            facts_node=facts_node,
            facts_edge=facts_edge,
            rules=rules,
            tmax=tmax,
            convergence_threshold=convergence_threshold,
            convergence_bound_threshold=convergence_bound_threshold,
            verbose=verbose,
        )

        # No PyReason result to compare; return a structured placeholder
        return {
            "match": False,
            "reason": "pyreason_result_missing",
            "native_only": nat_interp.get_dict(),
        }

    @staticmethod
    def dump_report(report: Dict[str, Any]) -> str:
        """
        Serialize a report dict to JSON string (stable keys).
        """
        try:
            return json.dumps(report, sort_keys=True, indent=2, default=str)
        except Exception:
            return str(report)