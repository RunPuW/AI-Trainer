"""
movementlibmodel
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON

from backend.db.session import Base


class Movement(Base):
    __tablename__ = "movements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)  #  text名
    name_en = Column(String(100), nullable=True)  # 英text名

    # splitclass
    category = Column(String(50))  # compound, isolation, cardio, flexibility, plyometric
    muscle_group = Column(String(50))  # mainneedtarget肌群
    secondary_muscles = Column(JSON, nullable=True)  # repneed肌群

    # property
    equipment = Column(String(50))  # placerequireMachine
    difficulty = Column(String(20))  # beginner, intermediate, advanced

    # 描述 ref导
    description = Column(Text, nullable=True)
    instructions = Column(JSON, nullable=True)  # stepspeak明
    key_points = Column(JSON, nullable=True)  # movementneedpoint
    common_mistakes = Column(JSON, nullable=True)  # 常见error

    # 媒body
    video_url = Column(String(500), nullable=True)
    image_urls = Column(JSON, nullable=True)

    # close联
    variations = Column(JSON, nullable=True)  # changebodymovementIDlist
    contraindications = Column(JSON, nullable=True)  # 禁忌injury病list

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
