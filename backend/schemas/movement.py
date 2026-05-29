"""
movementlibSchema
"""

from typing import Optional, List
from pydantic import BaseModel


class MovementResponse(BaseModel):
    id: str
    name: str
    name_en: Optional[str]
    category: Optional[str]
    muscle_group: Optional[str]
    secondary_muscles: Optional[List[str]]
    equipment: Optional[str]
    difficulty: Optional[str]
    description: Optional[str]
    instructions: Optional[List[str]]
    key_points: Optional[List[str]]
    common_mistakes: Optional[List[str]]
    video_url: Optional[str]
    contraindications: Optional[List[str]]

    class Config:
        from_attributes = True


class MovementCreate(BaseModel):
    name: str
    name_en: Optional[str] = None
    category: str
    muscle_group: str
    secondary_muscles: Optional[List[str]] = None
    equipment: str
    difficulty: str
    description: Optional[str] = None
    instructions: Optional[List[str]] = None
    key_points: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    video_url: Optional[str] = None
    contraindications: Optional[List[str]] = None
