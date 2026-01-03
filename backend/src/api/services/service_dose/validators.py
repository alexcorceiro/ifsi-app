from typing import Optional


class DoseValidator:
    def __init__(self, conn):
        self.conn = conn

    def validate_request(self, paylaod, *, context: str) -> None:
        allowed = {"FREE", "TRAINING_EXERCISE", "CLINICAL_CASE"}
        if context not in allowed:
            raise ValueError(f"context invalide: {context}.Valeurs: {sorted(allowed)}")
        
        if not paylaod.drug_name or not paylaod.drug_name.strip():
            raise ValueError("drug_name est requis")
        
        if context == "TRAINING_EXERCISE":
            if getattr(paylaod, "exercise_id", None) is None:
                raise ValueError("execise_id est requis quand context=TRAINING_EXERCISE")
            
        if context == "CLINICAL_CASE":
            if getattr(paylaod, "case_id", None) is None:
                raise ValueError("case_id est requis quand context=CLINICAL_CASE")
            
        if paylaod.weight_kg is not None and paylaod.weight_kg <= 0:
            raise ValueError("weight_kg doit etre > 0 si renseigné")
        
        if paylaod.patient_age_y is not None and paylaod.patient_age_y < 0:
            raise ValueError("patient_age_y doit etre >=0 si renseigne")
        
        if not isinstance(paylaod.dose_input, dict) or len(paylaod.dose_input) == 0:
            raise ValueError("dose_input doir etre un object")
        
        