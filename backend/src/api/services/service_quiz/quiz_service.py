from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
from datetime import timedelta

from core.quiz_repo import QuizRepo


def _norm_str (v: Any) -> str:
    return str(v or "").strip().lower()


def _extract_choice_ids(payload: Any) -> List[str]:
    if payload is None:
        return []
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, list):
        return [str(x) for x in payload if x is not None]
    if isinstance(payload, dict):
        for k in ("ids", "correct", "selected", "answers", "answer", "value", "id"):
            if k in payload and payload[k] is not None:
                return _extract_choice_ids(payload[k])
    return []

def grade_item(item: Dict[str, Any], student_answers: Dict[str, Any]) -> Tuple[Optional[bool], Dict[str, Any]]:
    """Retourne (is_correct, details). None si non-gradable."""
    itype = item.get("type")
    expected = item.get("bonne_reponse")

    # QCM (multi)
    if itype == "qcm":
        exp_ids = set(_extract_choice_ids(expected))
        stu_ids = set(_extract_choice_ids(student_answers))
        if not exp_ids:
            return None, {"reason": "no_expected_answer"}
        return exp_ids == stu_ids, {"expected": sorted(exp_ids), "given": sorted(stu_ids)}

    # Vrai/Faux
    if itype == "vf":
        exp = None
        if isinstance(expected, dict) and "value" in expected:
            exp = bool(expected["value"])
        elif isinstance(expected, bool):
            exp = bool(expected)

        given = None
        if isinstance(student_answers, dict) and "value" in student_answers:
            given = bool(student_answers["value"])
        elif isinstance(student_answers, bool):
            given = bool(student_answers)

        if exp is None or given is None:
            return None, {"reason": "missing_value"}
        return exp == given, {"expected": exp, "given": given}

   
    if itype == "carte":
        if expected is None:
            return None, {"reason": "no_expected_answer"}

        exp_texts: List[str] = []
        if isinstance(expected, dict):
            if "texts" in expected:
                exp_texts = [str(x) for x in (expected.get("texts") or [])]
            elif "text" in expected:
                exp_texts = [str(expected.get("text"))]
            elif "answers" in expected:
                exp_texts = [str(x) for x in (expected.get("answers") or [])]
        elif isinstance(expected, str):
            exp_texts = [expected]

        given_text = ""
        if isinstance(student_answers, dict):
            given_text = str(student_answers.get("text") or student_answers.get("value") or "")
        else:
            given_text = str(student_answers or "")

        exp_norm = {_norm_str(t) for t in exp_texts if _norm_str(t)}
        giv_norm = _norm_str(given_text)
        if not exp_norm or not giv_norm:
            return None, {"reason": "missing_text"}
        return giv_norm in exp_norm, {"expected": sorted(exp_norm), "given": given_text}

    return None, {"reason": "unknown_type"}




@dataclass
class AttemptStartResult:
    attempt: Dict[str, Any]
    item_order: List[int]
    options_order: Dict[int, List[str]]
    items: List[Dict[str, Any]] 


class QuizService:

    def __init__(self, conn):
        self.conn = conn

    def create_quiz(self, payload: Dict[str, Any]) -> int:
        with self.conn.cursor() as cur:
            return QuizRepo.create_quiz(cur, payload)
        
    def get_quiz(self, quiz_id: int) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            return QuizRepo.get_quiz(cur, quiz_id)

    def update_quiz(self, quiz_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            updated = QuizRepo.update_quiz(cur, quiz_id, payload)
        if updated is None:
            raise ValueError("Aucun champ à mettre à jour")
        return updated

    def create_item(self, quiz_id: int, payload: Dict[str, Any]) -> int:
        with self.conn.cursor() as cur:
            if not QuizRepo.get_quiz(cur, quiz_id):
                raise ValueError("quiz not found")
            return QuizRepo.create_item(cur, quiz_id, payload)


    def start_attempt(self, quiz_id: int, user_id: int, meta: Optional[Dict[str, Any]] = None) -> AttemptStartResult:
        meta = meta or {}
        with self.conn.cursor() as cur:
            quiz = QuizRepo.get_quiz(cur, quiz_id)
            if not quiz:
                raise ValueError("quiz not found")

            # limite de tentatives
            limit = quiz.get("attempts_limit")
            if limit is not None:
                n = QuizRepo.count_attempts_for_user(cur, quiz_id, user_id)
                if n >= int(limit):
                    raise ValueError("attempts_limit_reached")

            items = QuizRepo.list_items(cur, quiz_id)
            item_ids = [int(it["id"]) for it in items]
            if quiz.get("shuffle_items") and len(item_ids) > 1:
                random.shuffle(item_ids)

            # shuffle options: mémorise un ordre stable en meta
            options_order: Dict[int, List[str]] = {}
            if quiz.get("shuffle_options"):
                items_by_id = {int(it["id"]): it for it in items}
                for iid in item_ids:
                    it = items_by_id.get(iid) or {}
                    if it.get("type") == "qcm" and it.get("options_json"):
                        
                        ids = [str(o.get("id")) for o in (it.get("options_json") or []) if o.get("id") is not None]
                        if len(ids) > 1:
                            random.shuffle(ids)
                        options_order[iid] = ids

            meta2 = {
                **meta,
                "item_order": item_ids,
                "options_order": options_order,
                "score_max": len(item_ids),
            }

            attempt_id = QuizRepo.create_attempt(cur, quiz_id=quiz_id, user_id=user_id, meta=meta2)
            attempt = QuizRepo.get_attempt(cur, attempt_id)
            if not attempt:
                raise ValueError("attempt not created")


        items_by_id = {int(it["id"]): it for it in items}
        safe_items: List[Dict[str, Any]] = []
        for iid in item_ids:
            it = dict(items_by_id[iid])
            it.pop("bonne_reponse", None)
            safe_items.append(it)

        return AttemptStartResult(
            attempt=attempt,
            item_order=item_ids,
            options_order=options_order,
            items=safe_items,
        )

    def answer_item(self, attempt_id: int, item_id: int, answers_json: Dict[str, Any]) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            attempt = QuizRepo.get_attempt(cur, attempt_id)
            if not attempt:
                raise ValueError("attempt not found")
            if attempt.get("finished_at"):
                raise ValueError("attempt already finished")

     
            quiz = QuizRepo.get_quiz(cur, int(attempt["quiz_id"]))
            if quiz and quiz.get("duration_sec") and attempt.get("started_at"):
                deadline = attempt["started_at"] + timedelta(seconds=int(quiz["duration_sec"]))
                from datetime import datetime, timezone
                if datetime.now(timezone.utc) > deadline:
                    raise ValueError("attempt expired")

            item = QuizRepo.get_item(cur, item_id)
            if not item:
                raise ValueError("item not found")
            if int(item.get("quiz_id")) != int(attempt.get("quiz_id")):
                raise ValueError("item not in this quiz")

            is_correct, details = grade_item(item, answers_json)
            saved = QuizRepo.upsert_answer(
                cur,
                attempt_id=attempt_id,
                item_id=item_id,
                answers_json=answers_json,
                is_correct=is_correct,
            )

            feedback: Dict[str, Any] = {"is_correct": is_correct, "details": details}
            if is_correct is False and item.get("explication_md"):
                feedback["explication_md"] = item.get("explication_md")

        return {"answer": saved, "feedback": feedback}

    def finish_attempt(self, attempt_id: int) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            attempt = QuizRepo.get_attempt(cur, attempt_id)
            if not attempt:
                raise ValueError("attempt not found")

            if attempt.get("finished_at"):
                
                return {"attempt": attempt, "passed": None}

            quiz = QuizRepo.get_quiz(cur, int(attempt["quiz_id"]))
            if not quiz:
                raise ValueError("quiz not found")

            items = QuizRepo.list_items(cur, int(attempt["quiz_id"]))
            score_max = len(items)

            answers = QuizRepo.list_answers_for_attempt(cur, attempt_id)
            correct_by_item = {int(a["item_id"]): a.get("is_correct") for a in answers}

            score_raw = sum(1 for it in items if correct_by_item.get(int(it["id"])) is True)
            finished = QuizRepo.finish_attempt(cur, attempt_id=attempt_id, score_raw=score_raw, score_max=score_max)

            passed = None
            pass_mark = quiz.get("pass_mark")
            if pass_mark is not None and score_max > 0:
                pm = float(pass_mark)
                passed = (score_raw / score_max) >= pm if pm <= 1.0 else score_raw >= pm

        return {"attempt": finished, "score_raw": score_raw, "score_max": score_max, "passed": passed}