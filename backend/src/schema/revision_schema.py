from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

SheetStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
SheetItemType = Literal["BULLET","DEFINITION","FORMULA","STEP","WARNING","EXAMPLE","QA"]


class RevisionSheetCreateIn(BaseModel):
    course_id: int
    version_id: Optional[int] = None
    title: str = Field(..., min_length=1)
    status: SheetStatus = "DRAFT"
    content_md: Optional[str] = None

class RevisionSheetUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    status: Optional[SheetStatus] = None
    content_md: Optional[str] = None
    version_id: Optional[int] = None

class RevisionSheetOut(BaseModel):
    id: int
    course_id: int
    version_id: Optional[int]
    title: str
    status: str
    content_md: Optional[str]

class RevisionSheetItemCreateIn(BaseModel):
    sheet_id: int
    item_type: SheetItemType = "BULLET"
    position: int = Field(1, ge=1)
    title: Optional[str] = None
    body_md: str = Field(..., min_length=1)

    source_id: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None

class RevisionSheetItemOut(BaseModel):
    id: int
    sheet_id: int
    item_type: str
    position: int
    title: Optional[str]
    body_md: str
    source_id: Optional[int]
    page_start: Optional[int]
    page_end: Optional[int]


class NoteCreateIn(BaseModel):
    owner_id: Optional[int] = None
    ue_id: Optional[int] = None
    lesson_id: Optional[int] = None
    title: str = Field(..., min_length=1)
    content_md: str = Field(..., min_length=1)
    is_ai_generated: bool = False
    sources: List[Dict[str, Any]] = []

class NoteOut(BaseModel):
    id: int
    owner_id: Optional[int]
    ue_id: Optional[int]
    lesson_id: Optional[int]
    title: str
    content_md: str
    is_ai_generated: bool
    sources: List[Dict[str, Any]]

class FlashcardCreateIn(BaseModel):
    note_id: Optional[int] = None
    lesson_id: Optional[int] = None
    front_md: str = Field(..., min_length=1)
    back_md: str = Field(..., min_length=1)
    tags: List[str] = []

class FlashcardOut(BaseModel):
    id: int
    note_id: Optional[int]
    lesson_id: Optional[int]
    front_md: str
    back_md: str
    tags: List[str]



class SrsScheduleOut(BaseModel):
    id: int
    user_id: int
    flashcard_id: int
    interval_days: int
    ease_factor: float
    repetitions: int
    due_at: str

class SrsReviewIn(BaseModel):
    user_id: int
    flashcard_id: int
    quality: int = Field(..., ge=0, le=5)
    meta: Dict[str, Any] = {}