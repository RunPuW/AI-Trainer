"""
userprofileSchema
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel


class InjuryInfo(BaseModel):
    area: str
    severity: str  # mild, moderate, severe
    note: Optional[str] = None


class QuestionnaireSubmit(BaseModel):
    """ask卷provide交"""
    gender: str
    birth_date: date
    height_cm: float
    weight_kg: float
    body_fat_pct: Optional[float] = None
    fitness_level: str
    goal: str
    weekly_days: int
    session_minutes: int
    equipment: List[str]
    injuries: List[InjuryInfo] = []
    medical_notes: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    gender: Optional[str]
    birth_date: Optional[date]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    body_fat_pct: Optional[float]
    fitness_level: Optional[str]
    goal: Optional[str]
    weekly_days: Optional[int]
    session_minutes: Optional[int]
    equipment: Optional[List[str]]
    injuries: Optional[List[dict]]
    version: int

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    body_fat_pct: Optional[float] = None
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    weekly_days: Optional[int] = None
    session_minutes: Optional[int] = None
    equipment: Optional[List[str]] = None
