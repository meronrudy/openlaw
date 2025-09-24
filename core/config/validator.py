from __future__ import annotations

import sys
from typing import Any, Dict, List, Tuple

import yaml


def _read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML at {path} must be a mapping at top level")
    return data


def validate_burden_config(path: str) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    data = _read_yaml(path)

    if "DEFAULT_BURDEN" not in data:
        errs.append("DEFAULT_BURDEN missing")
    else:
        try:
            default = float(data["DEFAULT_BURDEN"])
            if not (0.0 <= default <= 1.0):
                errs.append("DEFAULT_BURDEN must be in [0,1]")
        except Exception:
            errs.append("DEFAULT_BURDEN must be numeric")

    overrides = data.get("BURDEN_OVERRIDES", {})
    if overrides and not isinstance(overrides, dict):
        errs.append("BURDEN_OVERRIDES must be a mapping")
    else:
        # Each jurisdiction -> mapping of claim -> float
        for juris, claims in overrides.items():
            if not isinstance(claims, dict):
                errs.append(f"BURDEN_OVERRIDES.{juris} must be a mapping")
                continue
            for claim, val in claims.items():
                try:
                    v = float(val)
                    if not (0.0 <= v <= 1.0):
                        errs.append(f"BURDEN_OVERRIDES.{juris}.{claim} must be in [0,1]")
                except Exception:
                    errs.append(f"BURDEN_OVERRIDES.{juris}.{claim} must be numeric")

    return (len(errs) == 0), errs


def validate_courts_config(path: str) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    data = _read_yaml(path)

    weights = data.get("weights", {})
    if not isinstance(weights, dict):
        errs.append("weights must be a mapping")
    else:
        for key in ("controlling", "persuasive", "contrary"):
            if key not in weights:
                errs.append(f"weights.{key} missing")
            else:
                try:
                    float(weights[key])
                except Exception:
                    errs.append(f"weights.{key} must be numeric")

    # Optional presence checks for federal/state blocks
    fed = data.get("federal", {})
    if fed and not isinstance(fed, dict):
        errs.append("federal must be a mapping")
    states = data.get("states", [])
    if states and not isinstance(states, list):
        errs.append("states must be a list")

    return (len(errs) == 0), errs


def validate_reporters_config(path: str) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    data = _read_yaml(path)

    canonical = data.get("canonical", {})
    if not isinstance(canonical, dict) or not canonical:
        errs.append("canonical mapping missing or not a mapping")
    else:
        # spot-check a few entries for structure
        for rep_key, rep_obj in list(canonical.items())[:5]:
            if not isinstance(rep_obj, dict):
                errs.append(f"canonical.{rep_key} must be a mapping")
                continue
            names = rep_obj.get("names")
            patterns = rep_obj.get("patterns")
            if not isinstance(names, list) or not names:
                errs.append(f"canonical.{rep_key}.names must be a non-empty list")
            if not isinstance(patterns, list) or not patterns:
                errs.append(f"canonical.{rep_key}.patterns must be a non-empty list")

    norm = data.get("normalization", {})
    if norm and not isinstance(norm, dict):
        errs.append("normalization must be a mapping if present")

    return (len(errs) == 0), errs


def validate_redaction_rules_config(path: str) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    data = _read_yaml(path)

    if data.get("mode") not in ("ingest_blocking", "dry_run"):
        errs.append("mode must be 'ingest_blocking' or 'dry_run'")
    if "patterns" not in data or not isinstance(data["patterns"], list):
        errs.append("patterns must be a list")
    else:
        for idx, pat in enumerate(data["patterns"]):
            if not isinstance(pat, dict):
                errs.append(f"patterns[{idx}] must be a mapping")
                continue
            if "regex" not in pat or "action" not in pat:
                errs.append(f"patterns[{idx}] missing 'regex' or 'action'")
            if pat.get("action") not in ("mask", "drop", "hash"):
                errs.append(f"patterns[{idx}].action must be one of mask|drop|hash")

    return (len(errs) == 0), errs


def validate_all(
    burden_path: str,
    courts_path: str,
    reporters_path: str,
    redaction_path: str,
) -> Tuple[bool, List[str]]:
    ok = True
    errors: List[str] = []

    v, e = validate_burden_config(burden_path)
    ok = ok and v
    errors.extend([f"burden.yml: {x}" for x in e])

    v, e = validate_courts_config(courts_path)
    ok = ok and v
    errors.extend([f"courts.yml: {x}" for x in e])

    v, e = validate_reporters_config(reporters_path)
    ok = ok and v
    errors.extend([f"reporters.yml: {x}" for x in e])

    v, e = validate_redaction_rules_config(redaction_path)
    ok = ok and v
    errors.extend([f"redaction_rules.yml: {x}" for x in e])

    return ok, errors


def main(argv: List[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    burden = "config/policy/burden.yml"
    courts = "config/normalize/courts.yml"
    reporters = "config/normalize/reporters.yml"
    redaction = "config/compliance/redaction_rules.yml"

    ok, errors = validate_all(burden, courts, reporters, redaction)
    if not ok:
        print("Config validation FAILED:")
        for e in errors:
            print(f" - {e}")
        return 2

    print("All configs valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())