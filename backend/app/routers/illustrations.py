import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..models import (
    IllustrationRequest, IllustrationResult,
    PRESET_LABELS, PromptVariant, PromptVariantCreate,
)
from ..services import imagen_service

router = APIRouter(prefix="/illustrations", tags=["illustrations"])

_VARIANTS_FILE = Path(__file__).parent.parent / "data" / "prompt_variants.json"
_VARIANTS_FILE.parent.mkdir(exist_ok=True)


def _load_variants() -> list[dict]:
    if _VARIANTS_FILE.exists():
        return json.loads(_VARIANTS_FILE.read_text())
    return []


def _save_variants(variants: list[dict]) -> None:
    _VARIANTS_FILE.write_text(json.dumps(variants, indent=2))


# ── Presets ───────────────────────────────────────────────────────────────────

@router.get("/presets")
async def list_presets():
    defaults = imagen_service.get_default_templates()
    return [
        {"id": k, "label": v, "default_template": defaults[k]}
        for k, v in PRESET_LABELS.items()
    ]


# ── Prompt variants ───────────────────────────────────────────────────────────

@router.get("/variants", response_model=list[PromptVariant])
async def list_variants():
    return [PromptVariant(**v) for v in _load_variants()]


@router.post("/variants", response_model=PromptVariant)
async def create_variant(body: PromptVariantCreate):
    variants = _load_variants()
    variant = PromptVariant(name=body.name, preset_type=body.preset_type, template=body.template)
    variants.append(variant.model_dump())
    _save_variants(variants)
    return variant


@router.put("/variants/{variant_id}", response_model=PromptVariant)
async def update_variant(variant_id: str, body: PromptVariantCreate):
    variants = _load_variants()
    for v in variants:
        if v["id"] == variant_id:
            v.update(name=body.name, preset_type=body.preset_type, template=body.template)
            _save_variants(variants)
            return PromptVariant(**v)
    raise HTTPException(status_code=404, detail="Variant not found")


@router.delete("/variants/{variant_id}")
async def delete_variant(variant_id: str):
    variants = _load_variants()
    variants = [v for v in variants if v["id"] != variant_id]
    _save_variants(variants)
    return {"deleted": variant_id}


# ── Generate ──────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=IllustrationResult)
async def generate_illustration(body: IllustrationRequest):
    custom_template: str | None = None
    variant_name: str | None = None

    if body.custom_template:
        custom_template = body.custom_template
        variant_name = "custom"
    elif body.variant_id:
        variants = _load_variants()
        match = next((v for v in variants if v["id"] == body.variant_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Variant not found")
        custom_template = match["template"]
        variant_name = match["name"]

    try:
        result = await imagen_service.generate_illustration(
            preset=body.preset,
            paper_context=body.paper_context,
            aspect_ratio=body.aspect_ratio,
            resolution=body.resolution,
            iteration=body.iteration,
            custom_template=custom_template,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc

    result.variant_name = variant_name
    return result
