from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    speaking_style = Column(Text, nullable=True)
    core_traits = Column(Text, nullable=True)
    core_values = Column(Text, nullable=True)
    avatar_image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="persona")
    memories = relationship("Memory", back_populates="persona", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="persona")
