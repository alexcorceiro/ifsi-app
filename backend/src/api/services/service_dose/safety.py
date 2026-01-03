from typing import Any, Dict, List


class DrugSafetyService:
    def __init__(self, conn):
        self.conn = conn

    def evaluate(
        self,
        *,
        drug_name: str,
        patient_age_y,
        weight_kg,
        dose_result: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        
        messages: List[str] = []
        rules_hit: List[Dict[str, Any]] = []




        return {"status": "OK", "messages": messages, "rules": rules_hit}