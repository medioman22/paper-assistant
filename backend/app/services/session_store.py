"""
Persistent session store.
Keeps sessions in memory for fast access and mirrors them to disk.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_STORE_FILE = _DATA_DIR / "sessions.json"
_PDF_DIR = _DATA_DIR / "pdfs"
_DATA_DIR.mkdir(exist_ok=True)
_PDF_DIR.mkdir(exist_ok=True)

_sessions: dict[str, dict] = {}

_STRIP_KEYS = {"paper_text", "chat_history", "illustrations", "pdf_path"}


def _load() -> None:
    if _STORE_FILE.exists():
        for s in json.loads(_STORE_FILE.read_text()):
            _sessions[s["session_id"]] = s


def _save() -> None:
    _STORE_FILE.write_text(json.dumps(list(_sessions.values()), indent=2))


_load()


def pdf_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()[:16]


def save_pdf(paper_hash: str, pdf_bytes: bytes) -> str:
    path = _PDF_DIR / f"{paper_hash}.pdf"
    if not path.exists():
        path.write_bytes(pdf_bytes)
    return str(path)


def load_pdf(paper_hash: str) -> bytes | None:
    path = _PDF_DIR / f"{paper_hash}.pdf"
    return path.read_bytes() if path.exists() else None


def find_by_hash(h: str) -> list[dict]:
    return [s for s in _sessions.values() if s["paper_hash"] == h]


def create(session_id: str, paper_hash: str, summary: dict, paper_text: str, pdf_path: str | None = None) -> dict:
    record = {
        "session_id": session_id,
        "paper_hash": paper_hash,
        "title": summary["title"],
        "abstract": summary["abstract"],
        "key_points": summary.get("key_points", []),
        "methodology": summary.get("methodology", ""),
        "findings": summary.get("findings", ""),
        "raw_text_excerpt": summary.get("raw_text_excerpt", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paper_text": paper_text,
        "chat_history": [],
        "illustrations": [],
        "pdf_path": pdf_path,
    }
    _sessions[session_id] = record
    _save()
    return record


def get(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def list_all() -> list[dict]:
    return sorted(_sessions.values(), key=lambda s: s["created_at"], reverse=True)


def delete(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _save()


def add_illustration(session_id: str, illustration: dict) -> None:
    s = _sessions.get(session_id)
    if s:
        s.setdefault("illustrations", []).append(illustration)
        _save()


def update_chat_history(session_id: str, history: list) -> None:
    s = _sessions.get(session_id)
    if s:
        s["chat_history"] = history
        _save()


def get_chat_history(session_id: str) -> list:
    s = _sessions.get(session_id)
    return s.get("chat_history", []) if s else []


def public_meta(s: dict) -> dict:
    """Strip heavy fields before sending to the frontend list."""
    return {k: v for k, v in s.items() if k not in _STRIP_KEYS}
