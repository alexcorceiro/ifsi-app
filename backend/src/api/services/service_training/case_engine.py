from typing import Dict, Any, Optional
from core.case_repo import CaseRepo
from utils.case_scoring import compute_case_score
from fastapi import HTTPException

def _to_dict(cur, row):
    """Supporte cursor dict OU tuple."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cols = [d[0] for d in cur.description] if cur.description else []
    return dict(zip(cols, row))


def _to_dicts(cur, rows):
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in rows]

class CaseEngineService:
    def __init__(self, conn):
        self.conn = conn
    
    def start_case(self, *, case_id: int, user_id: int) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            case_row = CaseRepo.get_case(cur, case_id)
            if not case_row:
                raise ValueError("case not found")

            attempt_id = CaseRepo.create_attempt(cur, user_id=user_id, case_id=case_id)

            # On renvoie directement l'état initial (step 1)
            state = self.get_attempt_state(attempt_id=attempt_id)

        self.conn.commit()
        return state

    
    def get_attempt_state(self, *, attempt_id: int) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            att = CaseRepo.get_attempt(cur, attempt_id)
            if not att:
                raise ValueError("attempt not found")

            case_id = att["case_id"]

            steps = CaseRepo.list_steps(cur, case_id)
            total_steps = len(steps)

            answered = CaseRepo.count_answers(cur, attempt_id)
            correct = CaseRepo.count_correct_answers(cur, attempt_id)

            score = 0.0 if total_steps == 0 else round((correct / total_steps) * 100, 2)
            completed = (answered >= total_steps) and (total_steps > 0)

            current_step = None
            if total_steps > 0 and not completed:
                pos = answered + 1
                step = CaseRepo.get_step_by_position(cur, case_id, pos)
                if step:
                    current_step = self._enrich_step(cur, step)

            CaseRepo.update_attempt_status(cur, attempt_id=attempt_id, score=score, completed=completed)

            return {
                "attempt_id": att["id"],
                "case_id": case_id,
                "completed": completed,
                "score": score,
                "progress": {"answered": answered, "total_steps": total_steps},
                "current_step": current_step,
            }

    def answer_step(
        self,
        *,
        attempt_id: int,
        step_id: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        payload attendu (minimal) :
        - pour MCQ: selected_choice_id
        - pour FREE: free_answer_text
        - pour CALC: free_answer_text OU plus tard integration dose/training
        - pour DECISION: selected_choice_id ou free_answer_text
        """
        with self.conn.cursor() as cur:
            att = CaseRepo.get_attempt(cur, attempt_id)
            if not att:
                raise ValueError("Tentative introuvable")

            step = CaseRepo.get_step(cur, step_id)
            if not step:
                raise ValueError("Étape introuvable")

            # ✅ Cohérence: l'étape doit appartenir au cas de la tentative
            if int(step["case_id"]) != int(att["case_id"]):
                raise ValueError("Cette étape n'appartient pas à ce cas clinique.")

            # Optionnel: empêcher de répondre 2 fois
            # existing = CaseRepo.get_answer(cur, attempt_id=attempt_id, step_id=step_id)
            # if existing: raise ValueError("Étape déjà répondue")

            step_type = (step.get("step_type") or "").upper()
            selected_choice_id = payload.get("selected_choice_id")
            free_answer_text = payload.get("free_answer_text")

            # Correction
            is_correct = False
            feedback_md = None

            if step_type == "MCQ":
                if not selected_choice_id:
                    raise ValueError("selected_choice_id est requis pour un QCM.")
                choice = CaseRepo.get_choice(cur, int(selected_choice_id))
                if not choice or int(choice["step_id"]) != int(step_id):
                    raise ValueError("Choix invalide pour cette étape.")
                is_correct = bool(choice["is_correct"])
                feedback_md = choice.get("feedback_md")

            elif step_type in ("FREE", "CALC", "DECISION"):
                # Pour l'instant: sans règle métier stockée en DB, on ne peut pas “corriger” un FREE/CALC proprement.
                # Donc: on enregistre la réponse, et is_correct reste False par défaut,
                # sauf si tu ajoutes une mécanique dans metadata (recommandé).
                if (free_answer_text is None or str(free_answer_text).strip() == "") and not selected_choice_id:
                    raise ValueError("Réponse requise (free_answer_text ou selected_choice_id).")

                # Si DECISION en QCM => même logique que MCQ
                if step_type == "DECISION" and selected_choice_id:
                    choice = CaseRepo.get_choice(cur, int(selected_choice_id))
                    if not choice or int(choice["step_id"]) != int(step_id):
                        raise ValueError("Choix invalide pour cette étape.")
                    is_correct = bool(choice["is_correct"])
                    feedback_md = choice.get("feedback_md")

                # Sinon: on laisse is_correct = False (à upgrader avec metadata / IA)
                # Tu peux aussi décider is_correct=True par défaut pour FREE (validation manuelle).
                # is_correct = False

            else:
                raise ValueError(f"step_type non supporté: {step_type}")

            # Persist answer
            answer_id = CaseRepo.insert_or_update_answer(
                cur,
                attempt_id=attempt_id,
                step_id=step_id,
                selected_choice_id=selected_choice_id,
                free_answer_text=free_answer_text,
                is_correct=is_correct,
            )

            # Update score & completed
            total_steps = CaseRepo.count_steps(cur, att["case_id"])
            answered = CaseRepo.count_answers(cur, attempt_id)
            correct = CaseRepo.count_correct_answers(cur, attempt_id)

            completed = answered >= total_steps and total_steps > 0
            score = (correct / total_steps) * 100 if total_steps else 0

            CaseRepo.update_attempt_status(cur, attempt_id=attempt_id, score=score, completed=completed)

            # step suivant
            steps = CaseRepo.list_steps(cur, att["case_id"])
            answers = CaseRepo.list_answers(cur, attempt_id)
            answered_step_ids = {a["step_id"] for a in answers}

            next_step = None
            for s in steps:
                if s["id"] not in answered_step_ids:
                    next_step = s
                    break

            next_step_hydrated = self._hydrate_step(cur, next_step) if next_step else None

            self.conn.commit()

            return {
                "answer_id": answer_id,
                "is_correct": is_correct,
                "feedback_md": feedback_md,
                "score": score,
                "completed": completed,
                "next_step": next_step_hydrated,
            }
        
    def _hydrate_step(self, cur, step_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not step_row:
            return None
        step_id = step_row["id"]
        choices = CaseRepo.list_choices(cur, step_id)
        return {
            "id": step_row["id"],
            "case_id": step_row["case_id"],
            "position": step_row["position"],
            "prompt_md": step_row["prompt_md"],
            "step_type": step_row["step_type"],
            "choices": [
                {
                    "id": c["id"],
                    "position": c["position"],
                    "label": c["label"],
                    # On ne renvoie PAS is_correct au client (sinon triche)
                    "feedback_md": c.get("feedback_md"),
                }
                for c in choices
            ],
        }
    
    def _enrich_step(self, cur, step: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(step)
        step_type = (out.get("step_type") or "").upper()

        if step_type == "MCQ":
            choices = CaseRepo.list_choices(cur, out["id"])
            choices = _to_dicts(cur, choices)

            # On cache is_correct au client (sinon triche)
            out["choices"] = [
                {"id": c["id"], "position": c["position"], "label": c["label"]}
                for c in choices
            ]
        else:
            out["choices"] = []

        return out