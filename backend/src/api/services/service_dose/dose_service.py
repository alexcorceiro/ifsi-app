from __future__ import annotations
from typing import Any, Dict, Optional
from core.dose_repo import DoseRepo
from api.services.service_dose.validators import DoseValidator
from api.services.service_dose.calculator import DoseCalculator
from api.services.service_dose.safety import DrugSafetyService
from schema.dose_schema import DoseCalculateIn


def calculate_from_dict(self, payload_dict: dict) -> dict:
    payload = DoseCalculateIn(**payload_dict)
    return self.calculate(payload)


class DoseService:
    def __init__(self, conn):
        self.conn = conn
        self.validator = DoseValidator(conn)
        self.calculator = DoseCalculator(conn)
        self.safety = DrugSafetyService(conn)

    

    def calculate(self, payload) -> Dict[str, Any]:
        context = (payload.context or "FREE")
        context = context.strip().upper() if isinstance(context, str) else str(context).strip().upper()

        self.validator.validate_request(payload, context=context)

        dose_result = self.calculator.compute(payload, context=context)

        safety = self.safety.evaluate(
            drug_name=payload.drug_name,
            patient_age_y=payload.patient_age_y,
            weight_kg=payload.weight_kg,
            dose_result=dose_result,
            context=context,
        )
        dose_result["safety"] = safety

        with self.conn.cursor() as cur:
            calc_id = DoseRepo.insert_calculation(
                cur,
                user_id=payload.user_id,
                context=context,
                exercise_id=getattr(payload, "exercise_id", None),
                case_id=getattr(payload, "case_id", None),
                patient_age_y=payload.patient_age_y,
                weight_kg=payload.weight_kg,
                drug_name=payload.drug_name,
                dose_input=payload.dose_input,
                dose_result=dose_result,
            )
        self.conn.commit()

        return {"calculation_id": calc_id, "dose_result": dose_result}