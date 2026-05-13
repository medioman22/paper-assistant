import os
import re
import json
from google import genai
from google.genai import types

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


PROMPT = """You are a scientific literature expert. Based on the paper below, suggest exactly 5 related papers most valuable to a researcher studying this topic.

Include a mix of:
- Papers directly cited in this paper (if identifiable)
- Foundational / seminal works in this area
- Parallel contemporary work
- Subsequent work building on similar ideas

Rules:
- Only suggest papers you are highly confident actually exist with these exact details.
- Provide a real URL (arXiv, DOI, Semantic Scholar, ACM DL, IEEE Xplore — whichever is most stable).
- Keep takeaway to one sentence explaining relevance to the paper above.

Return ONLY a valid JSON array, no markdown:
[
  {
    "title": "exact paper title",
    "authors": "First Author et al.",
    "year": 2020,
    "venue": "NeurIPS / Nature / arXiv / ...",
    "relationship": "cited | foundational | parallel | subsequent",
    "takeaway": "one sentence on why this is relevant",
    "url": "https://..."
  }
]

--- PAPER ---
Title: {title}
Abstract: {abstract}
Key points: {key_points}
Methodology: {methodology}
Findings: {findings}
"""


async def get_recommendations(title: str, abstract: str, key_points: list[str],
                              methodology: str, findings: str) -> list[dict]:
    client = _get_client()
    prompt = PROMPT.format(
        title=title, abstract=abstract,
        key_points="; ".join(key_points),
        methodology=methodology, findings=findings,
    )
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    raw = response.text.strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    start = raw.find("[")
    if start == -1:
        raise ValueError(f"No JSON array in response: {raw[:300]}")
    try:
        result, _ = json.JSONDecoder().raw_decode(raw, start)
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e} — raw excerpt: {raw[start:start+300]}")
