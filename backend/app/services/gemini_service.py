import os
import json
import asyncio
from google import genai
from google.genai import types
from ..models import PaperSummary

_client: genai.Client | None = None

EXTRACT_MODEL = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


SUMMARY_PROMPT = """You are a scientific paper analyst. Analyze the attached PDF and return ONLY valid JSON with this exact schema:
{
  "title": "string",
  "abstract": "string (1-2 sentences)",
  "key_points": ["string", ...],
  "methodology": "string (2-3 sentences)",
  "findings": "string (2-3 sentences)",
  "raw_text_excerpt": "string (first 300 characters of body text)"
}
No markdown, no explanation — JSON only."""

TEXT_EXTRACT_PROMPT = "Extract and return the full plain text of this PDF document. No formatting, no commentary — just the text."


async def summarize_paper(pdf_bytes: bytes) -> tuple[PaperSummary, str]:
    """Returns (summary, full_paper_text). Both Gemini calls run in parallel."""
    client = _get_client()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    summary_resp, text_resp = await asyncio.gather(
        client.aio.models.generate_content(
            model=EXTRACT_MODEL,
            contents=[pdf_part, SUMMARY_PROMPT],
        ),
        client.aio.models.generate_content(
            model=EXTRACT_MODEL,
            contents=[pdf_part, TEXT_EXTRACT_PROMPT],
        ),
    )

    raw = summary_resp.text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    summary = PaperSummary(**data)
    paper_text = text_resp.text.strip()

    return summary, paper_text
