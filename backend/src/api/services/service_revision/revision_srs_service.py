from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

from core.revision_srs_repo import RevisionSrsRepo


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _sm2(interval_days: int, ease_factor: float, repetitions: int, quality: int):
    q = quality
    ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if ef < 1.3:
        ef = 1.3

    if q < 3:
        return 1, ef, 0  # reset

    repetitions += 1
    if repetitions == 1:
        interval_days = 1
    elif repetitions == 2:
        interval_days = 6
    else:
        interval_days = int(round(interval_days * ef))
        if interval_days < 1:
            interval_days = 1

    return interval_days, ef, repetitions

class RevisionSrsService:
    def __init__(self, conn):
        self.conn = conn

    # Flashcards
    def create_flashcard(self, payload: Dict[str, Any]) -> int:
        with self.conn.cursor() as cur:
            return RevisionSrsRepo.create_flashcard(cur, payload)

    def list_flashcards(self, *, lesson_id: Optional[int], note_id: Optional[int], tag: Optional[str], limit: int, offset: int):
        with self.conn.cursor() as cur:
            return RevisionSrsRepo.list_flashcards(cur, lesson_id=lesson_id, note_id=note_id, tag=tag, limit=limit, offset=offset)

    def update_flashcard(self, flashcard_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            updated = RevisionSrsRepo.update_flashcard(cur, flashcard_id, payload)
            if updated is None:
                card = RevisionSrsRepo.get_flashcard(cur, flashcard_id)
                if card is None:
                    raise ValueError("flashcard not found")
                return card
            return updated

    def delete_flashcard(self, flashcard_id: int) -> bool:
        with self.conn.cursor() as cur:
            ok = RevisionSrsRepo.delete_flashcard(cur, flashcard_id)
            if not ok:
                raise ValueError("flashcard not found")
            return True

    # SRS
    def due(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            items = RevisionSrsRepo.list_due(cur, user_id, limit)
            return {"items": items, "due_count": len(items)}

    def review(self, user_id: int, flashcard_id: int, quality: int, meta: Dict[str, Any]) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            schedule = RevisionSrsRepo.get_schedule(cur, user_id, flashcard_id)
            if schedule is None:
                # lazy init : dû maintenant
                schedule = RevisionSrsRepo.upsert_schedule(
                    cur,
                    user_id=user_id,
                    flashcard_id=flashcard_id,
                    interval_days=1,
                    ease_factor=2.5,
                    repetitions=0,
                    due_at_iso=_now_utc().isoformat(),
                )

            interval_days = int(schedule["interval_days"])
            ease_factor = float(schedule["ease_factor"])
            repetitions = int(schedule["repetitions"])

            new_interval, new_ef, new_rep = _sm2(interval_days, ease_factor, repetitions, quality)
            due_at = _now_utc() + timedelta(days=new_interval)

            review_id = RevisionSrsRepo.insert_review(cur, user_id, flashcard_id, quality, meta or {})
            new_schedule = RevisionSrsRepo.upsert_schedule(
                cur,
                user_id=user_id,
                flashcard_id=flashcard_id,
                interval_days=new_interval,
                ease_factor=new_ef,
                repetitions=new_rep,
                due_at_iso=due_at.isoformat(),
            )

            return {"review_id": review_id, "schedule": new_schedule}

    def stats(self, user_id: int) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            return RevisionSrsRepo.stats_7d(cur, user_id)