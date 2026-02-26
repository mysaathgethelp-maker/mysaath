from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.memory import Memory
from app.schemas.schemas import ChatRequest, ChatResponse, ChatMessageOut
from app.services.billing_service import enforce_chat_limit
from app.services.prompt_service import assemble_prompt
from app.services.groq_service import call_groq, GroqError

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = current_user.persona
    if not persona:
        raise HTTPException(status_code=400, detail="Create a persona before chatting.")

    # Enforce plan limits
    enforce_chat_limit(db, current_user)

    # Load memories (all, sorted by priority)
    memories = (
        db.query(Memory)
        .filter(Memory.persona_id == persona.id)
        .all()
    )

    # Load recent chat history for context
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.persona_id == persona.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
        .all()
    )
    history = [{"role": row.role, "content": row.content} for row in history_rows]

    # Assemble layered prompt
    messages = assemble_prompt(persona, memories, payload.message, history)

    # Call Groq
    try:
        ai_reply = await call_groq(messages, max_tokens=600)
    except GroqError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Persist both turns
    db.add(ChatMessage(user_id=current_user.id, persona_id=persona.id, role="user", content=payload.message))
    db.add(ChatMessage(user_id=current_user.id, persona_id=persona.id, role="assistant", content=ai_reply))
    db.commit()

    return ChatResponse(reply=ai_reply, persona_name=persona.display_name)


@router.get("/history", response_model=List[ChatMessageOut])
def get_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = current_user.persona
    if not persona:
        raise HTTPException(status_code=400, detail="No persona found.")

    return (
        db.query(ChatMessage)
        .filter(ChatMessage.persona_id == persona.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )


@router.delete("/history", status_code=204)
def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = current_user.persona
    if not persona:
        raise HTTPException(status_code=400, detail="No persona found.")

    db.query(ChatMessage).filter(ChatMessage.persona_id == persona.id).delete()
    db.commit()
