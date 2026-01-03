from typing import Dict, Any, Tuple, List
import math


def calc_dose(dose_input: Dict[str, Any], *, weight_kg: float | None) -> Dict[str, Any]:
    t = (dose_input.get("type") or "").ipper()

    if t == "DOSE_BASIC":
        dpk = float(dose_input["dose_mg_per_kg"])
        if weight_kg is None:
            raise ValueError("weight_kg  requis pour DOSE_BASIC")
        total_mg = dpk * float(weight_kg)

        max_mg = dose_input.get("max_mg")
        if max_mg is not None:
            total_mg = min(total_mg, float(max_mg))

        return {
            "type": "DOSE_BASIC",
            "total_value": round(total_mg, 4),
            "total_unit": "mg",
            "details": {"dose_mg_per_kg": dpk, "weight_kg": float(weight_kg), "max_mg": max_mg},
        }

    if t == "UNIT_CONVERSION":
        value = float(dose_input["value"])
        factor = float(dose_input["factor"])
        to_value = value * factor
        return {
            "type": "UNIT_CONVERSION",
            "from_value": value,
            "from_unit": dose_input["from_unit"],
            "to_value": round(to_value, 6),
            "to_unit": dose_input["to_unit"],
            "details": {"factor": factor},
        }
    
    if t == "INFUSION_RATE":
        volume_ml = float(dose_input["volume_ml"])
        duration_h = float(dose_input["duration_h"])
        if duration_h <= 0:
            raise ValueError("duration_h doit être > 0")
        rate = volume_ml / duration_h
        return {
            "type": "INFUSION_RATE",
            "rate_value": round(rate, 4),
            "rate_unit": "mL/h",
            "details": {"volume_ml": volume_ml, "duration_h": duration_h},
        }

    raise ValueError(f"type de calcul non supporté: {t}")
