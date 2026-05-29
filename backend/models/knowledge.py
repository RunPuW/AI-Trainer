"""
knowknowlibmodel
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, JSON

from backend.db.session import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False)  # training_theory, nutrition, sports_medicine, recovery, equipment
    subcategory = Column(String(100), nullable=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
