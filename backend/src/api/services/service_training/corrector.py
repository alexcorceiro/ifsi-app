# src/api/services/service_training/corrector.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

from core.training_repo import TrainingRepo
from utils.scoring import grade_attempt
from api.services.service_training.dose_input_buider import DoseInputBuilder

try:
    from api.services.service_dose.dose_service import DoseService
except Exception:
    DoseService = None


def _row_to_dict_if_needed(row, cur=None):
    """
    Airbag : si row est un tuple, et qu'on a cur.description, on convertit.
    Normalement inutile si TrainingRepo.get_exercise renvoie déjà un dict.
    """
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if cur is None or cur.description is None:
        raise ValueError("Row tuple reçu sans description cursor (impossible de convertir).")
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return dict(zip(cols, row))


def build_feedback_items(error_codes: List[str], details: Dict[str, Any]) -> List[Dict[str, Any]]:
    mapping = {
        "MISSING_VALUE": (5, "Tu n’as pas renseigné de valeur. Mets un nombre puis recommence."),
        "MISSING_UNIT": (4, "Il manque l’unité : en calcul de dose, l’unité fait partie de la réponse."),
        "UNIT_ERROR": (4, "L’unité est incorrecte. Vérifie mg/g, mL/L, UI…"),
        "MG_G_CONFUSION": (3, "Rappel : **1 g = 1000 mg**. Conversion très fréquente."),
        "ML_L_CONFUSION": (3, "Rappel : **1 L = 1000 mL**."),
        "VALUE_ERROR": (4, "La valeur ne correspond pas. Reprends la formule et les étapes."),
        "FACTOR_1000_ERROR": (3, "On dirait un facteur ×1000 ou ÷1000. Revois la conversion."),
        "VALUE_NOT_NUMERIC": (5, "La valeur soumise n’est pas un nombre exploitable."),
        "EXERCISE_CONFIG_ERROR": (5, "Exercice mal configuré côté système (expected incomplet)."),
    }

    items: List[Dict[str, Any]] = []
    for code in error_codes:
        sev, msg = mapping.get(code, (2, f"Erreur détectée : **{code}**"))
        items.append({"code": code, "severity": sev, "message_md": msg, "meta": details})
    items.sort(key=lambda x: x["severity"], reverse=True)
    return items


def build_ai_feedback_md(
    is_correct: bool,
    score: float,
    feedback_items: List[Dict[str, Any]],
    details: Dict[str, Any],
) -> Optional[str]:
    if is_correct:
        return (
            "✅ **Bravo !**\n\n"
            f"Ta réponse est correcte (score **{score:.0f}/100**).\n"
            "Garde ce réflexe : **unité + ordre de grandeur**."
        )

    lines = [
        "### Correction (pas à pas)",
        f"- Score : **{score:.0f}/100**",
        "- Points à vérifier :",
    ]
    for it in feedback_items[:4]:
        lines.append(f"  - {it['message_md']}")
    lines.append("\n💡 Astuce : refais le calcul en écrivant la formule, puis contrôle l’unité.")
    return "\n".join(lines)


class TrainingCorrectorService:
    def __init__(self, conn):
        self.conn = conn
        self.dose_service = DoseService(conn) if DoseService else None

    def submit_attempt(self, *, exercise: Dict[str, Any], attempt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Corrige une tentative, enregistre attempt + feedback, et optionnellement trace core.dose_calculations.
        """
        # Sécurité : s'assurer que l'exercice est bien un dict
        if not isinstance(exercise, dict):
            # Normalement n'arrivera plus si TrainingRepo.get_exercise est corrigé
            exercise = dict(exercise)

        expected = exercise.get("expected") or {}

        is_correct, score, error_codes, details = grade_attempt(
            expected,
            attempt_payload.get("submitted_value"),
            attempt_payload.get("submitted_unit"),
        )

        feedback_items = build_feedback_items(error_codes, details)
        ai_feedback_md = build_ai_feedback_md(is_correct, score, feedback_items, details)

        calculation_id: Optional[int] = None
        meta = exercise.get("metadata") or {}
        dose_input_template = meta.get("dose_input_template")

        # Trace dose_calculations si possible
        if self.dose_service and dose_input_template:
            sj = attempt_payload.get("submitted_json") or {}
            drug_name = sj.get("drug_name") or meta.get("drug_name") or exercise.get("title") or "UNKNOWN"

            calc_payload = {
                "user_id": attempt_payload.get("user_id"),
                "context": "TRAINING_EXERCISE",
                "patient_age_y": sj.get("patient_age_y"),
                "weight_kg": sj.get("weight_kg"),
                "drug_name": drug_name,
                "dose_input": dose_input_template,
            }

            if hasattr(self.dose_service, "calculate_from_dict"):
                try:
                    res = self.dose_service.calculate_from_dict(calc_payload)
                    calculation_id = res.get("calculation_id")
                except Exception:
                    calculation_id = None

        try:
            with self.conn.cursor() as cur:
                attempt_id = TrainingRepo.create_attempt(
                    cur,
                    user_id=attempt_payload["user_id"],
                    exercise_id=exercise["id"],
                    submitted_json=attempt_payload.get("submitted_json", {}),
                    submitted_value=attempt_payload.get("submitted_value"),
                    submitted_unit=attempt_payload.get("submitted_unit"),
                    is_correct=is_correct,
                    score=score,
                    error_codes=error_codes,
                    ai_feedback_md=ai_feedback_md,
                    calculation_id=calculation_id,
                    time_ms=attempt_payload.get("time_ms"),
                )

                for item in feedback_items:
                    TrainingRepo.insert_attempt_feedback(
                        cur,
                        attempt_id=attempt_id,
                        code=item["code"],
                        severity=item["severity"],
                        message_md=item["message_md"],
                        meta=item.get("meta", {}),
                    )

            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        return {
            "id": attempt_id,
            "is_correct": is_correct,
            "score": float(score),
            "error_codes": error_codes,
            "ai_feedback_md": ai_feedback_md,
            "calculation_id": calculation_id,
            "feedback_items": feedback_items,
        }

    
    def _call_dose(self, calc_payload: Dict[str, Any]) -> Optional[int]:
        if not self.dose_service :
            return None
        
        with self.conn.cursor() as cur:
            if hasattr(self.dose_service, "calculate_and_store"):
                calculation_id, _ = self.dose_service.calculate_and_store(cur, calc_payload)
                return calculation_id
            
            return None
        
    def correct_calc_step(
        self,
        *,
        expected: Dict[str, Any],
        attempt_payload: Dict[str, Any],
        mode: str,
        template: Dict[str, Any],
        case_id: Optional[int] = None,
        exercise_id: Optional[int] = None
    ) -> Dict[str, Any]:
        
      if mode == "FULL":
            full = attempt_payload.get("full") or {}
            dose_input = full.get("dose_input")
            weight_kg = full.get("weight_kg")
            patient_age_y = full.get("patient_age_y")
            drug_name = full.get("drug_name") or attempt_payload.get("drug_name") or "UNKNOWN"

            submitted_value = attempt_payload.get("submitted_value")
            submitted_unit = attempt_payload.get("submitted_unit")

      else:  # MIX
            mix = attempt_payload.get("mix") or {}
            submitted_value = mix.get("submitted_value")
            submitted_unit = mix.get("submitted_unit")
            weight_kg = mix.get("weight_kg")
            patient_age_y = mix.get("patient_age_y")
            drug_name = mix.get("drug_name") or "UNKNOWN"

            dose_input = DoseInputBuilder.build_from_mix(template=template, mix=mix)

      is_correct, score, error_codes, details = grade_attempt(
            expected,
            submitted_value,
            submitted_unit
        )

      calculation_id = None
      if dose_input:
            calc_payload = DoseInputBuilder.build_calc_payload(
                user_id=attempt_payload["user_id"],
                context="CLINICAL_CASE" if case_id else "TRAINING_EXERCISE",
                exercise_id=exercise_id,
                case_id=case_id,
                patient_age_y=patient_age_y,
                weight_kg=weight_kg,
                drug_name=drug_name,
                dose_input=dose_input,
            )
            calculation_id = self._call_dose(calc_payload)

      return {
            "is_correct": is_correct,
            "score": score,
            "error_codes": error_codes,
            "details": details,
            "calculation_id": calculation_id,
        }  
