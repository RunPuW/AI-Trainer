"""
userprofilemodel
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.session import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # 基础info
    gender = Column(String(10))  # male, female, other
    birth_date = Column(Date)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    body_fat_pct = Column(Float, nullable=True)

    # training相close
    fitness_level = Column(String(20))  # beginner, intermediate, advanced
    goal = Column(String(50))  # lose_fat, gain_muscle, strength, endurance, rehab, general
    weekly_days = Column(Integer)  # perweektraining天num
    session_minutes = Column(Integer)  # perreptrainingwhenlong

    # Machine injury病
    equipment = Column(JSON)  # ["barbell", "dumbbell", "cable", ...]
    injuries = Column(JSON)  # [{"area": "knee", "severity": "mild", "note": "..."}]
    medical_notes = Column(Text, nullable=True)

    # squat基linedata
    squat_baseline = Column(JSON, nullable=True)  # usersquat基lineanglerange

    # 原始ask卷
    questionnaire = Column(JSON, nullable=True)

    # 版thisctrlmake
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # relation
    user = relationship("User", back_populates="profile")
