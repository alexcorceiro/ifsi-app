from typing import Any, Dict
from decimal import Decimal
from api.services.service_dose.units import UnitsService, UnitError

class DoseCalculator:
    def __init__(self, conn):
        self.conn = conn
        self.units = UnitsService(conn)

    def compute(self, payload, * , context: str) -> Dict[str, Any]:
        dose_input = payload.dose_input or {}
        calc_type = (dose_input.get("type") or "").strip().upper()
        if not calc_type:
            raise ValueError("dose_input.type est requis (ex: MG_KG, VOLUME_FROM_CONCENTRATION, ...).")

        if calc_type  == "MG_KG":
            prescribed = dose_input.get("prescribed") or {}
            val = prescribed.get("value", None)
            unit_raw = prescribed.get("unit", None)

            if val is None:
                raise ValueError("MG_KG: prescribed.value est requis.")
            if not unit_raw:
                raise ValueError("MG_KG: prescribed.unit est requis (ex: mg/kg, mcg/kg, g/kg).")
            
            from_unit = self.units.units.normalize_unit_code(unit_raw) if hasattr(self.units, "units") else None
            from_unit = str(unit_raw).strip()
            
            if payload.weight_kg is None:
                raise ValueError("MG_KG: weight_kg est requis pour calculer une dose absolue.")
            if float(payload.weight_kg) <= 0:
                raise ValueError("MG_KG: weight_kg doit être > 0.")

            try:
                mg_per_kg = self.units.convert_compound(val, from_unit, "mg/kg")
                total_mg, out_unit = self.units.to_absolute_dose(mg_per_kg, "mg/kg", weight_kg=payload.weight_kg)
            except UnitError as e:
                raise ValueError(f"MG_KG: erreur unité/conversion: {e}")

            mg_per_kg_disp = mg_per_kg.quantize(Decimal("0.0001"))
            total_mg_disp = total_mg.quantize(Decimal("0.0001"))

            steps = [
                {"label": "Formule", "calc": "Dose (mg) = posologie (mg/kg) × poids (kg)"},
            ]

            unit_lower = str(unit_raw).strip().lower().replace("μ", "µ")
            if unit_lower not in {"mg/kg", "mg/kg/j", "mg/kg/jour"}:
                steps.append(
                    {"label": "Conversion d’unité",
                     "calc": f"{val} {unit_raw} = {mg_per_kg_disp} mg/kg"}
                )

            steps.append(
                {"label": "Application",
                 "calc": f"{mg_per_kg_disp} × {payload.weight_kg} = {total_mg_disp} mg"}
            )

            return {
                "status": "OK",
                "type": "MG_KG",
                "answer": {"value": float(total_mg_disp), "unit": "mg"},
                "canonical": {
                    "prescribed": {"value": float(mg_per_kg_disp), "unit": "mg/kg"},
                    "weight_kg": float(payload.weight_kg),
                },
                "steps": steps,
                "explanations": [
                    "On convertit d’abord la posologie en mg/kg (unité canonique), "
                    "puis on multiplie par le poids pour obtenir la dose totale en mg."
                ],
                "warnings": []
            }


        raise ValueError(f"type de calcul non supporté: {calc_type}")