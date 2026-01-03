from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal

DoseContext = Literal["FREE", "TRAINING_EXERCISE", "CLINICAL_CASE"]

class DoseCalculateIn(BaseModel):
    user_id: Optional[int] = None
    context: DoseContext = "FREE"

    # IMPORTANT : pour correspondre à la table core.dose_calculations
    exercise_id: Optional[int] = None
    case_id: Optional[int] = None

    patient_age_y: Optional[float] = None
    weight_kg: Optional[float] = None

    drug_name: str = Field(..., min_length=1)
    dose_input: Dict[str, Any]

    @field_validator("drug_name")
    @classmethod
    def normalize_drug_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        if v is None:
            return "FREE"
        if isinstance(v, str):
            return v.strip().upper()
        return v

class DoseCalculateOut(BaseModel):
    calculation_id: int
    dose_result: Dict[str, Any]


class DoseCalculatuionUpdateIn(BaseModel):
    context: Optional[DoseContext] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v if v else None
    
class DoseCalculationOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    context: DoseContext
    exercise_id: Optional[int] = None
    case_id: Optional[int] = None
    patient_age_y: Optional[float] = None
    weight_kg: Optional[float] = None
    drug_name: str
    dose_input: Dict[str, Any]
    dose_result: Dict[str, Any]
    notes: Optional[str] = None