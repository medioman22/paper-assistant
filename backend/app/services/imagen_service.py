import os
import base64
from google import genai
from google.genai import types
from ..models import PresetType, PRESET_LABELS, IllustrationResult, AspectRatio, Resolution

_client: genai.Client | None = None

IMAGE_MODEL = "nano-banana-pro-preview"

DEFAULT_TEMPLATES: dict[PresetType, str] = {
    "sketch": (
        "Create a minimal technical pencil sketch illustration summarizing the key concept of this research paper. "
        "Style: fine pencil line drawing on white background, monochromatic, precise scientific diagram aesthetic, "
        "clean elegant lines with subtle hatching for depth, academic figure style, no color fills, "
        "refined and sophisticated — suitable for a premium research portfolio website. "
        "Paper context:\n{context}"
    ),
    "key_concept": (
        "Create a clean educational diagram illustrating the core concept of this research paper. "
        "Use clear labels, arrows, and visual hierarchy. "
        "Style: scientific textbook illustration, white background, clear typography. "
        "Paper context:\n{context}"
    ),
    "process_workflow": (
        "Create a step-by-step process flow diagram representing the methodology of this research paper. "
        "Use boxes, arrows, and numbered steps. "
        "Style: modern flowchart, clean design, white background. "
        "Paper context:\n{context}"
    ),
    "infographic": (
        "Create a visually engaging infographic summarizing the key findings of this research paper. "
        "Include data visualizations, icons, and concise text. "
        "Style: modern scientific infographic, colorful but professional, white background. "
        "Paper context:\n{context}"
    ),
    "metaphorical": (
        "Create an artistic metaphorical illustration capturing the essence of this research paper "
        "through visual storytelling and symbolism. "
        "Style: conceptual art, thoughtful composition, evocative imagery. "
        "Paper context:\n{context}"
    ),
}

_RATIO_DIMS: dict[str, tuple[int, int]] = {
    "1:1":  (1, 1),
    "16:9": (16, 9),
    "4:3":  (4, 3),
    "9:16": (9, 16),
}


def _resolution_hint(resolution: Resolution, aspect_ratio: AspectRatio) -> str:
    base = int(resolution)
    rx, ry = _RATIO_DIMS[aspect_ratio]
    if rx >= ry:
        w, h = base, int(base * ry / rx)
    else:
        h, w = base, int(base * rx / ry)
    return f"Image dimensions: {w}x{h} pixels, aspect ratio {aspect_ratio}."


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


async def generate_illustration(
    preset: PresetType,
    paper_context: str,
    aspect_ratio: AspectRatio = "1:1",
    resolution: Resolution = "2048",
    iteration: int = 1,
    custom_template: str | None = None,
) -> IllustrationResult:
    client = _get_client()

    template = custom_template or DEFAULT_TEMPLATES[preset]
    body = template.format(context=paper_context[:1500])
    dim_hint = _resolution_hint(resolution, aspect_ratio)
    prompt = f"{dim_hint}\n\n{body}"

    response = await client.aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    image_part = next(
        (p for p in response.candidates[0].content.parts if p.inline_data),
        None,
    )
    if image_part is None:
        raise RuntimeError("Model returned no image")

    mime = image_part.inline_data.mime_type
    image_b64 = base64.b64encode(image_part.inline_data.data).decode()

    return IllustrationResult(
        preset=preset,
        label=PRESET_LABELS[preset],
        image_b64=image_b64,
        mime_type=mime,
        prompt_used=prompt,
        iteration=iteration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )


def get_default_templates() -> dict[str, str]:
    return dict(DEFAULT_TEMPLATES)
