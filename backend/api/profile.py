"""
User profile and questionnaire API.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.deps import get_current_user
from backend.models.user import User
from backend.models.profile import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class InjuryInfo(BaseModel):
    area: str
    severity: str = "mild"
    note: Optional[str] = None


class QuestionnaireData(BaseModel):
    gender: str = "male"
    birth_date: Optional[str] = None
    height_cm: float = 170.0
    weight_kg: float = 70.0
    body_fat_pct: Optional[float] = None
    fitness_level: str = "beginner"
    goal: str = "general"
    weekly_days: int = 3
    session_minutes: int = 60
    equipment: List[str] = ["bodyweight"]
    injuries: List[InjuryInfo] = []
    medical_notes: Optional[str] = None


class ProfileResponse(BaseModel):
    username: str
    questionnaire: Optional[QuestionnaireData] = None


@router.post("/questionnaire", response_model=ProfileResponse)
async def submit_questionnaire(
    data: QuestionnaireData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update user profile questionnaire."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    birth = None
    if data.birth_date:
        try:
            birth = date.fromisoformat(data.birth_date)
        except ValueError:
            pass

    injury_dicts = [i.model_dump() for i in data.injuries]

    if profile is None:
        profile = UserProfile(
            user_id=current_user.id,
            gender=data.gender,
            birth_date=birth,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            body_fat_pct=data.body_fat_pct,
            fitness_level=data.fitness_level,
            goal=data.goal,
            weekly_days=data.weekly_days,
            session_minutes=data.session_minutes,
            equipment=data.equipment,
            injuries=injury_dicts,
            medical_notes=data.medical_notes,
            questionnaire=data.model_dump(),
        )
        db.add(profile)
    else:
        profile.gender = data.gender
        profile.birth_date = birth
        profile.height_cm = data.height_cm
        profile.weight_kg = data.weight_kg
        profile.body_fat_pct = data.body_fat_pct
        profile.fitness_level = data.fitness_level
        profile.goal = data.goal
        profile.weekly_days = data.weekly_days
        profile.session_minutes = data.session_minutes
        profile.equipment = data.equipment
        profile.injuries = injury_dicts
        profile.medical_notes = data.medical_notes
        profile.questionnaire = data.model_dump()

    db.commit()
    db.refresh(current_user)

    return ProfileResponse(
        username=current_user.username,
        questionnaire=data,
    )


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    questionnaire = None
    if profile and profile.questionnaire:
        try:
            questionnaire = QuestionnaireData(**profile.questionnaire)
        except Exception:
            pass

    return ProfileResponse(
        username=current_user.username,
        questionnaire=questionnaire,
    )
