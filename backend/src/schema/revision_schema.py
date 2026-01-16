from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

# --- Enums / Literals ---
SheetStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
TargetType = Literal["ue", "course", "lesson", "section", "competency", "anatomy_node"]

SheetItemType = Literal[
    "BULLET", "DEFINITION", "FORMULA", "STEP", "WARNING", "EXAMPLE", "QA", "HEADING", "SECTION"
]

AssetType = Literal["IMAGE"]
AssetAnchor = Literal["PAGE", "ITEM", "ABSOLUTE"]


# =========================
# Revision Sheets
# =========================
class RevisionSheetCreateIn(BaseModel):
    # compat (ancien)
    course_id: Optional[int] = None
    version_id: Optional[int] = None

    # nouveau (générique)
    target_type: Optional[TargetType] = None
    target_id: Optional[int] = None

    title: str = Field(..., min_length=1)
    status: SheetStatus = "DRAFT"
    content_md: Optional[str] = None


class RevisionSheetUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    status: Optional[SheetStatus] = None
    content_md: Optional[str] = None
    version_id: Optional[int] = None
    target_type: Optional[TargetType] = None
    target_id: Optional[int] = None
    course_id: Optional[int] = None  # compat


class RevisionSheetOut(BaseModel):
    id: int
    course_id: Optional[int]
    version_id: Optional[int]
    target_type: Optional[str]
    target_id: Optional[int]
    title: str
    status: str
    content_md: Optional[str]


# =========================
# Sheet Items (blocks)
# =========================
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


# =========================
# Sheet Assets (images)
# =========================
class SheetAssetCreateIn(BaseModel):
    sheet_id: int
    asset_type: AssetType = "IMAGE"

    source_id: Optional[int] = None
    file_url: Optional[str] = None

    anchor: AssetAnchor = "PAGE"
    anchor_item_id: Optional[int] = None

    page_no: int = Field(1, ge=1)
    x: float = 0
    y: float = 0
    w: float = 100
    h: float = 100
    z_index: int = 0

    caption_md: Optional[str] = None
    meta: Dict[str, Any] = {}


class SheetAssetOut(BaseModel):
    id: int
    sheet_id: int
    asset_type: str
    source_id: Optional[int]
    file_url: Optional[str]
    anchor: str
    anchor_item_id: Optional[int]
    page_no: int
    x: float
    y: float
    w: float
    h: float
    z_index: int
    caption_md: Optional[str]
    meta: Dict[str, Any]


# =========================
# Notes
# =========================
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


# =========================
# Flashcards
# =========================
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


# =========================
# SRS
# =========================
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



class FlashcardUpdateIn(BaseModel): 
    note_id: Optional[int] = None
    lesson_id: Optional[int] = None
    front_md: Optional[str] = Field(default=None, min_length=1)
    back_md: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[List[str]] = None

class SrsDueOut(BaseModel):
    items: List[Dict[str, Any]]
    due_count: int

class SrsReviewOut(BaseModel):
    review_id:int
    schedule: Dict[str, Any]

class SrsStatusOut(BaseModel):
    user_id: int
    due_now: int
    reviews_7d: int
    avg_quality_7d: float
