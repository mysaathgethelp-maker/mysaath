from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.memory import Memory
from app.schemas.schemas import MemoryCreate, MemoryUpdate, MemoryOut
from app.services.billing_service import enforce_memory_limit

router = APIRouter()


def _get_persona_or_404(user: User):
    if not user.persona:
        raise HTTPException(status_code=404, detail="Create a persona first.")
    return user.persona


def _get_memory_or_404(db: Session, memory_id: int, persona_id: int) -> Memory:
    memory = db.query(Memory).filter(Memory.id == memory_id, Memory.persona_id == persona_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return memory


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(
    payload: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = _get_persona_or_404(current_user)
    enforce_memory_limit(db, current_user)

    memory = Memory(persona_id=persona.id, **payload.model_dump())
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.get("", response_model=List[MemoryOut])
def list_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = _get_persona_or_404(current_user)
    return (
        db.query(Memory)
        .filter(Memory.persona_id == persona.id)
        .order_by(Memory.created_at.desc())
        .all()
    )


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = _get_persona_or_404(current_user)
    return _get_memory_or_404(db, memory_id, persona.id)


@router.put("/{memory_id}", response_model=MemoryOut)
def update_memory(
    memory_id: int,
    payload: MemoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = _get_persona_or_404(current_user)
    memory = _get_memory_or_404(db, memory_id, persona.id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(memory, field, value)

    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=204)
def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = _get_persona_or_404(current_user)
    memory = _get_memory_or_404(db, memory_id, persona.id)
    db.delete(memory)
    db.commit()
