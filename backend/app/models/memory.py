import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class MemoryType(str, enum.Enum):
    trait = "trait"
    value = "value"
    phrase = "phrase"
    episodic = "episodic"


class MemoryPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    memory_type = Column(Enum(MemoryType), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(Enum(MemoryPriority), default=MemoryPriority.medium, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    persona = relationship("Persona", back_populates="memories")
