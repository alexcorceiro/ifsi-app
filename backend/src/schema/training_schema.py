from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal

ExerciseType = Literal[
    "DOSE_BASIC", "DILUTION", "INFUSION_RATE", "CONCENTRATION",
    "PEDIATRIC", "UNIT_CONVERSION", "MIXED"
]
ExerciseSource = Literal["TEACHER", "AI", "IMPORT"]


class ExerciseCreateIn(BaseModel):
    title: str = Field(..., min_length=1)
    statement_md: str = Field(..., min_length=1)
    exercise_type: ExerciseType = "DOSE_BASIC"
    difficulty: int = Field(1, ge=1, le=10)  # ✅ le=10 (pas 1)
    tags: List[str] = Field(default_factory=list)

    # expected recommandé :
    # { "answer": {"value": 250, "unit": "mg"}, "tolerance_rel": 0.02, "accepted_units": ["mg"] }
    expected: Dict[str, Any] = Field(default_factory=dict)

    # steps pédagogiques (facultatif)
    solution_steps: List[Dict[str, Any]] = Field(default_factory=list)

    created_by: Optional[int] = None
    source: ExerciseSource = "TEACHER"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExerciseOut(BaseModel):
    id: int
    title: str
    statement_md: str
    exercise_type: str
    difficulty: int
    tags: List[str]
    expected: Dict[str, Any]
    solution_steps: List[Dict[str, Any]]
    source: str
    metadata: Dict[str, Any]

class CalcMixIn(BaseModel):
    submitted_value: float
    submitted_unit: str = Field(..., min_length=1)
    weight_kg: Optional[float] = None
    patient_age_y: Optional[float] = None
    drug_name: Optional[str] = None
    extra: Dict[str, Any] = {}

class CalcFullIn(BaseModel):
    dose_input: Dict[str, Any] = Field(..., description=" meme strucutre que /dos/calculate")
    weight_kg: Optional[float] = None
    patient_age_y: Optional[float] = None
    drug_name: Optional[str] = None


AttemptMode = Literal["MIX", "FULL"]


class CaseStepAnswerIn(BaseModel):
    mode: AttemptMode= "MIX"
    selected_choice_id: Optional[int] = None
    free_answer_text: Optional[str] = None
    mix: Optional[CalcMixIn] = None
    full: Optional[CalcFullIn] = None

class AttemptCreateIn(BaseModel):
    user_id: int
    submitted_json: Dict[str, Any] = Field(default_factory=dict)
    submitted_value: Optional[float] = None
    submitted_unit: Optional[str] = None
    time_ms: Optional[int] = None


class AttemptOut(BaseModel):
    id: int
    is_correct: bool
    score: float
    error_codes: List[str]
    ai_feedback_md: Optional[str] = None
    calculation_id: Optional[int] = None


class AttemptFeedbackOut(BaseModel):
    code: str
    severity: int
    message_md: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class AttemptSubmitOut(AttemptOut):
    feedback_items: List[AttemptFeedbackOut] = Field(default_factory=list)
