from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from math import isclose

def _norm_unit(u: Optional[str]) -> Optional[str]:
    if u is None:
        return None
    return u.strip().lower().replace(" ", "")

def grade_attempt(
    expected: Dict[str, Any],
    submitted_value: Optional[float],
    submitted_unit: Optional[str],
) -> Tuple[bool, float, List[str], Dict[str, Any]]:
    """
    expected recommandé:
      {
        "answer": {"value": 250, "unit": "mg"},
        "tolerance_rel": 0.02,
        "accepted_units": ["mg"]
      }
    """
    error_codes: List[str] = []
    details: Dict[str, Any] = {}

    ans = expected.get("answer") or {}
    exp_val = ans.get("value")
    exp_unit = _norm_unit(ans.get("unit"))

    if exp_val is None or not exp_unit:
        return False, 0.0, ["EXERCISE_CONFIG_ERROR"], {"expected": expected}

    tol_rel = float(expected.get("tolerance_rel", 0.02))
    tol_abs = float(expected.get("tolerance_abs", 1e-6))
    accepted_units = expected.get("accepted_units") or [exp_unit]
    accepted_units = [_norm_unit(u) for u in accepted_units if u]

    if submitted_value is None:
        return False, 0.0, ["MISSING_VALUE"], {"expected_value": exp_val, "expected_unit": exp_unit}

    sub_unit = _norm_unit(submitted_unit)
    if not sub_unit:
        return False, 0.0, ["MISSING_UNIT"], {"expected_value": exp_val, "expected_unit": exp_unit}

    # Unit checks
    if sub_unit not in accepted_units:
        error_codes.append("UNIT_ERROR")
        if {sub_unit, exp_unit} == {"mg", "g"}:
            error_codes.append("MG_G_CONFUSION")
        if {sub_unit, exp_unit} == {"ml", "l"}:
            error_codes.append("ML_L_CONFUSION")

    try:
        sub_val = float(submitted_value)
    except Exception:
        return False, 0.0, ["VALUE_NOT_NUMERIC"], {"submitted_value": submitted_value}

    ok_value = isclose(sub_val, float(exp_val), rel_tol=tol_rel, abs_tol=tol_abs)
    if not ok_value:
        error_codes.append("VALUE_ERROR")
        # heuristique x1000 / /1000
        if float(exp_val) != 0:
            ratio = sub_val / float(exp_val)
            if isclose(ratio, 1000.0, rel_tol=0.03) or isclose(ratio, 0.001, rel_tol=0.03):
                error_codes.append("FACTOR_1000_ERROR")

    details.update({
        "expected_value": float(exp_val),
        "expected_unit": exp_unit,
        "submitted_value": sub_val,
        "submitted_unit": sub_unit,
        "accepted_units": accepted_units,
        "tolerance_rel": tol_rel,
    })

    if not error_codes:
        return True, 100.0, [], details

    # Score dégressif (simple, efficace)
    score = 100.0
    penalties = {
        "MISSING_VALUE": 80,
        "MISSING_UNIT": 60,
        "UNIT_ERROR": 35,
        "MG_G_CONFUSION": 15,
        "ML_L_CONFUSION": 15,
        "VALUE_ERROR": 35,
        "FACTOR_1000_ERROR": 20,
        "VALUE_NOT_NUMERIC": 80,
        "EXERCISE_CONFIG_ERROR": 100,
    }
    for c in error_codes:
        score -= penalties.get(c, 10)
    score = max(0.0, min(100.0, score))

    return False, score, sorted(list(set(error_codes))), details
