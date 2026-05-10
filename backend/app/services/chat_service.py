import os
import json
from google import genai
from google.genai import types
from ..models import ChatResponse, ChatSource
from . import session_store

_client: genai.Client | None = None

# In-memory sessions: session_id → {paper_text, history}
_sessions: dict[str, dict] = {}


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def create_session(session_id: str, paper_text: str) -> None:
    history = session_store.get_chat_history(session_id)
    _sessions[session_id] = {"paper_text": paper_text, "history": history}


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


CHAT_SYSTEM = """You are a research assistant helping a user understand an academic paper.
You have access to the full paper text provided below.

Answer questions accurately and helpfully. You are encouraged to use both:
1. The paper text — for specific claims, numbers, methodology, findings in this paper
2. Your general knowledge — for background concepts, definitions, comparisons, or anything the paper does not cover

Rules for sources:
- For every claim drawn from the paper, add a source with type "paper" and an exact verbatim quote.
- For every claim drawn from your general knowledge (not explicitly in the paper), add a source with type "web" and a brief description of what you are drawing on (e.g. "General knowledge: transformer architecture background").
- Every answer must have at least one source entry.
- If the question is entirely outside the paper, all sources should be type "web".

You MUST respond with valid JSON only, matching this schema exactly:
{
  "answer": "your answer text here",
  "sources": [
    {"type": "paper", "quote": "exact verbatim quote from the paper"},
    {"type": "web", "quote": "General knowledge: brief description of external knowledge used"}
  ]
}

No markdown, no extra text — JSON only.

--- PAPER TEXT ---
{paper_text}
"""


async def ask(session_id: str, question: str) -> ChatResponse:
    session = _sessions.get(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    client = _get_client()
    system = CHAT_SYSTEM.replace("{paper_text}", session["paper_text"][:40_000])

    # Build conversation history for multi-turn context
    history_msgs = []
    for turn in session["history"][-6:]:  # keep last 3 exchanges
        history_msgs.append({"role": "user", "parts": [{"text": turn["question"]}]})
        history_msgs.append({"role": "model", "parts": [{"text": turn["raw_answer"]}]})

    history_msgs.append({"role": "user", "parts": [{"text": question}]})

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=history_msgs,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
        ),
    )

    raw = response.text.strip()
    # Extract the JSON object robustly regardless of markdown fences or preamble
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")
    data = json.loads(raw[start:end])

    sources = [ChatSource(**s) for s in data.get("sources", [])]
    answer = data.get("answer", "")

    session["history"].append({"question": question, "raw_answer": raw})
    session_store.update_chat_history(session_id, session["history"])

    return ChatResponse(answer=answer, sources=sources)
