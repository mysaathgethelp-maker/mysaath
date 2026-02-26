from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.persona import Persona
from app.schemas.schemas import PersonaCreate, PersonaUpdate, PersonaOut

router = APIRouter()


@router.post("", response_model=PersonaOut, status_code=201)
def create_persona(
    payload: PersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.persona:
        raise HTTPException(status_code=400, detail="You already have a persona. Use PUT to update.")

    persona = Persona(user_id=current_user.id, **payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.get("", response_model=PersonaOut)
def get_persona(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.persona:
        raise HTTPException(status_code=404, detail="No persona found. Create one first.")
    return current_user.persona


@router.put("", response_model=PersonaOut)
def update_persona(
    payload: PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = current_user.persona
    if not persona:
        raise HTTPException(status_code=404, detail="No persona found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)

    db.commit()
    db.refresh(persona)
    return persona


@router.delete("", status_code=204)
def delete_persona(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = current_user.persona
    if not persona:
        raise HTTPException(status_code=404, detail="No persona found.")
    db.delete(persona)
    db.commit()
