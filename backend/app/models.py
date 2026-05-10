from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
import uuid

PresetType = Literal[
    "sketch",
    "key_concept",
    "process_workflow",
    "infographic",
    "metaphorical",
]

PRESET_LABELS: dict[PresetType, str] = {
    "sketch": "Pencil Sketch",
    "key_concept": "Key Concept Diagram",
    "process_workflow": "Process / Workflow",
    "infographic": "Infographic Summary",
    "metaphorical": "Metaphorical Illustration",
}

AspectRatio = Literal["1:1", "16:9", "4:3", "9:16"]
Resolution = Literal["512", "1024", "2048", "4096"]


# ── Paper ─────────────────────────────────────────────────────────────────────

class PaperSummary(BaseModel):
    title: str
    abstract: str
    key_points: list[str]
    methodology: str
    findings: str
    raw_text_excerpt: str


class SessionMeta(BaseModel):
    session_id: str
    title: str
    abstract: str
    created_at: str
    paper_hash: str


class UploadResponse(BaseModel):
    session_id: str
    summary: PaperSummary
    duplicate_sessions: list[SessionMeta] = []


# ── Prompt variants ───────────────────────────────────────────────────────────

class PromptVariant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    preset_type: PresetType | None = None  # None = standalone custom prompt
    template: str


class PromptVariantCreate(BaseModel):
    name: str
    preset_type: PresetType | None = None
    template: str


# ── Illustrations ─────────────────────────────────────────────────────────────

class IllustrationRequest(BaseModel):
    preset: PresetType
    paper_context: str
    aspect_ratio: AspectRatio = "1:1"
    resolution: Resolution = "2048"
    iteration: int = 1
    variant_id: str | None = None       # use a saved variant; overrides default template
    custom_template: str | None = None  # one-off override (e.g. from chat)


class IllustrationResult(BaseModel):
    preset: PresetType
    label: str
    image_b64: str
    mime_type: str = "image/jpeg"
    prompt_used: str
    iteration: int = 1
    aspect_ratio: AspectRatio = "1:1"
    resolution: Resolution = "2048"
    variant_name: str | None = None


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatSource(BaseModel):
    type: Literal["paper", "web"]
    quote: str
    url: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
