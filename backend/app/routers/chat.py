from fastapi import APIRouter, HTTPException
from ..models import ChatRequest, ChatResponse
from ..services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def ask_question(body: ChatRequest):
    if not chat_service.get_session(body.session_id):
        raise HTTPException(status_code=404, detail="Session not found. Re-upload the paper.")
    try:
        return await chat_service.ask(body.session_id, body.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
