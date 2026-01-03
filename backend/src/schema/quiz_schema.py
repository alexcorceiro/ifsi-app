from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


QuizMode = Literal["entrainement", "examen_blanc","diagnostic"]
QuizItemType = Literal["qcm", "vf","carte"]

class QuizCreateIn(BaseModel):
    titre: str = Field(..., min_length=1)
    tags: List[str] = []
    niveau: Optional[str] = None
    is_published: bool = False
    mode: QuizMode = "entrainement"
    duration_sec: Optional[int] = Field(default=None, ge=30, le=7200)
    pass_mark: Optional[float] = None
    shuffle_items: bool = True
    shuffle_options: bool = True
    attempts_limit: Optional[int] = Field(default=None, ge=1)
    created_by: Optional[int] = None

class QuizUpdateIn(BaseModel):
    titre: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[List[str]] = None
    niveau: Optional[str] = None
    is_published: Optional[bool] = None
    mode: Optional[QuizMode] = None
    duration_sec: Optional[int] = Field(default=None, ge=30, le=7200)
    pass_mark: Optional[float] = None
    shuffle_items: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    attempts_limit: Optional[int] = Field(default=None, ge=1)

class QuizOut(BaseModel):
    id: int
    titre: str
    tags: List[str]
    niveau: Optional[str]
    is_published: bool
    mode: str
    duration_sec: Optional[int]
    pass_mark: Optional[float]
    shuffle_items: bool
    shuffle_options: bool
    attempts_limit: Optional[int]
    created_by: Optional[int]

# -------------------------
# QUIZ ITEM
# -------------------------

class QuizItemCreateIn(BaseModel):
    type: QuizItemType = "qcm"
    question_md: str = Field(..., min_length=1)

    # qcm => tableau d'options [{"id":"A","label":"..."}, ...]
    options_json: Optional[List[Dict[str, Any]]] = None

    # réponse attendue (qcm/vf/carte) sous forme json
    bonne_reponse: Optional[Dict[str, Any]] = None

    explication_md: Optional[str] = None
    ordre: int = 0
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    tags: List[str] = []

class QuizItemOut(BaseModel):
    id: int
    quiz_id: int
    type: str
    question_md: str
    options_json: Optional[Dict[str, Any]] = None
    bonne_reponse: Optional[Dict[str, Any]] = None
    explication_md: Optional[str] = None
    ordre: int
    difficulty: Optional[int]
    tags: List[str]

# -------------------------
# QUIZ ATTEMPT / ANSWER
# -------------------------

class QuizAttemptStartIn(BaseModel):
    user_id: int
    meta: Dict[str, Any] = {}

class QuizAttemptOut(BaseModel):
    id: int
    quiz_id: int
    user_id: int
    started_at: str
    finished_at: Optional[str] = None
    score_raw: Optional[int] = None
    score_max: Optional[int] = None
    meta: Dict[str, Any] = {}

class QuizAnswerIn(BaseModel):
    answers_json: Dict[str, Any] = Field(default_factory=dict)

class QuizAnswerOut(BaseModel):
    id: int
    attempt_id: int
    item_id: int
    answers_json: Dict[str, Any]
    is_correct: Optional[bool] = None
    responded_at: str


