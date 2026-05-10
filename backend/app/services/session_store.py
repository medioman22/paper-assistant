"""
Persistent session store.
Keeps sessions in memory for fast access and mirrors them to disk.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

_STORE_FILE = Path(__file__).parent.parent / "data" / "sessions.json"
_STORE_FILE.parent.mkdir(exist_ok=True)

# {session_id: {session_id, paper_hash, title, abstract, created_at, paper_text}}
_sessions: dict[str, dict] = {}


def _load() -> None:
    if _STORE_FILE.exists():
        for s in json.loads(_STORE_FILE.read_text()):
            _sessions[s["session_id"]] = s


def _save() -> None:
    _STORE_FILE.write_text(json.dumps(list(_sessions.values()), indent=2))


_load()


def pdf_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()[:16]


def find_by_hash(h: str) -> list[dict]:
    return [s for s in _sessions.values() if s["paper_hash"] == h]


def create(session_id: str, paper_hash: str, title: str, abstract: str, paper_text: str) -> dict:
    record = {
        "session_id": session_id,
        "paper_hash": paper_hash,
        "title": title,
        "abstract": abstract,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paper_text": paper_text,
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


def public_meta(s: dict) -> dict:
    """Strip paper_text before sending to the frontend."""
    return {k: v for k, v in s.items() if k != "paper_text"}
