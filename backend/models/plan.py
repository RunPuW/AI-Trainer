"""
trainingplanmodel
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.session import Base


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    profile_id = Column(String, ForeignKey("user_profiles.id"), nullable=True)

    # planinfo
    title = Column(String(200))
    goal = Column(String(50))
    split_type = Column(String(50))  # full_body, upper_lower, push_pull_legs, bro_split, custom
    duration_weeks = Column(Integer)
    current_week = Column(Integer, default=1)
    status = Column(String(20), default="draft")  # draft, active, paused, completed, archived

    # plandata
    plan_data = Column(JSON)  # completeplanendstruct
    ai_reasoning = Column(Text, nullable=True)  # AIgeneratereason由
    rag_sources = Column(JSON, nullable=True)  # RAGpull_upusecome源

    # 版thisctrlmake
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # relation
    user = relationship("User", back_populates="plans")
