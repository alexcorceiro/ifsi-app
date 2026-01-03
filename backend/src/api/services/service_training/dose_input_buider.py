from typing import Dict, Any, Optional


class DoseInputBuilder:
    @staticmethod
    def build_form_mix(*, template: Dict[str, Any], mix: Dict[str, Any]) -> Dict[str, Any]:
        dose_input= dict(template)


        return dose_input
    
    @staticmethod
    def build_calc_paylaod(
        *, user_id: int,
        context: str,
        exercise_id: Optional[int],
        case_id: Optional[int],
        patient_age_y: Optional[float],
        weight_kg: Optional[float],
        drug_name: str,
        dose_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "context": context,
            "exercise_id": exercise_id,
            "case_id": case_id,
            "patient_age_y": patient_age_y,
            "weight_kg": weight_kg,
            "drug_name": drug_name,
            "dose_input": dose_input,
        }