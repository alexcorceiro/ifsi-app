from __future__ import annotations
from typing import Any, Dict
from core.training_repo import TrainingRepo

class TrainingGeneratorService:
    def __init__(self, conn):
        self.conn = conn

    def create_exercise(self, payload):
        with self.conn.cursor() as cur:
            ex_id = TrainingRepo.create_exercise(cur, payload)
        self.conn.commit()
        return ex_id