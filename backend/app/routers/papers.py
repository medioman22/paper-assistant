import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..models import UploadResponse, PaperSummary, IllustrationResult
from ..services import gemini_service, chat_service, session_store

router = APIRouter(prefix="/papers", tags=["papers"])


def _summary_from_record(s: dict) -> PaperSummary:
    return PaperSummary(
        title=s["title"],
        abstract=s["abstract"],
        key_points=s.get("key_points", []),
        methodology=s.get("methodology", ""),
        findings=s.get("findings", ""),
        raw_text_excerpt=s.get("raw_text_excerpt", ""),
    )


@router.get("/sessions")
async def list_sessions():
    return [session_store.public_meta(s) for s in session_store.list_all()]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    s = session_store.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if not chat_service.get_session(session_id):
        chat_service.create_session(session_id, s["paper_text"])
    illustrations = [IllustrationResult(**i) for i in s.get("illustrations", [])]
    chat_history = [
        {"question": t["question"], "answer": t.get("answer", ""), "sources": t.get("sources", [])}
        for t in s.get("chat_history", [])
    ]
    return {
        "session_id": s["session_id"],
        "summary": _summary_from_record(s),
        "created_at": s["created_at"],
        "illustrations": [i.model_dump() for i in illustrations],
        "chat_history": chat_history,
    }


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    session_store.delete(session_id)


@router.post("/upload", response_model=UploadResponse)
async def upload_paper(file: UploadFile = File(...), force: bool = Form(False)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB).")

    h = session_store.pdf_hash(pdf_bytes)
    duplicates = [session_store.public_meta(s) for s in session_store.find_by_hash(h)]

    # Return duplicates immediately without processing — let the user decide first
    if duplicates and not force:
        return UploadResponse(
            session_id="",
            summary=PaperSummary(title="", abstract="", key_points=[], methodology="", findings="", raw_text_excerpt=""),
            duplicate_sessions=duplicates,
            is_new_session=False,
        )

    try:
        summary, paper_text = await gemini_service.summarize_paper(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Paper analysis failed: {exc}") from exc

    pdf_path = session_store.save_pdf(h, pdf_bytes)
    session_id = str(uuid.uuid4())
    chat_service.create_session(session_id, paper_text)
    session_store.create(session_id, h, summary.model_dump(), paper_text, pdf_path)

    return UploadResponse(session_id=session_id, summary=summary, duplicate_sessions=duplicates, is_new_session=True)
