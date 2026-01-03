from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any


stepType = Literal["MCQ", "FREE", "CALC","DESCISION"]


class CaseOut(BaseModel):
    id: int
    title: str
    intro_md: str
    difficulty: int
    tags: Optional[List[str]] = None

class CaseStartIn(BaseModel):
    user_id: int

class CaseAttemptOut(BaseModel):
    id: int
    case_id: int
    user_id: int
    score: float
    complated: bool
    current_step_id: Optional[int] = None

class StepAnswerIn(BaseModel):
    selected_choice_id: Optional[int] = None
    free_answer_text: Optional[str] = None
    meta: Dict[str, Any] = {}

class CaseAnswerIn(BaseModel):
    selected_choice_id: Optional[int] = None
    free_answer_text: Optional[str] = None

    