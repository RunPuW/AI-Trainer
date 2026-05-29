"""
traininglogmodel
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.session import Base


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)

    # traininginfo
    session_date = Column(Date, nullable=False)
    day_label = Column(String(50))  # "Day 1 - Push"
    duration_min = Column(Integer)

    # trainingdata
    exercises = Column(JSON)  # movementlist及groupnum详情
    exercise_type = Column(String(50), nullable=True)  # trainingtype
    rep_count = Column(Integer, nullable=True)  # totalcount
    errors = Column(JSON, nullable=True)  # detectionto error
    error_details = Column(JSON, nullable=True)  # errortype计num详情
    angles_log = Column(JSON, nullable=True)  # anglelog(used_for回放)

    # main观评价
    rpe_avg = Column(Float, nullable=True)  # averageRPE
    mood = Column(String(20))  # great, good, ok, bad, terrible
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relation
    user = relationship("User", back_populates="workouts")
