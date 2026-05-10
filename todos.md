# Paper Assistant — TODO

## Backlog

_(empty)_

---

## Done

### Core pipeline
- [x] PDF upload → Gemini 2.0 Flash extracts full text + structured summary (title, abstract, key points, methodology, findings)
- [x] Session ID returned on upload; full paper text stored server-side for chat context
- [x] Session persistence to disk (`backend/app/data/sessions.json`); sessions survive backend restarts
- [x] Duplicate paper detection on upload — prompts user to resume a previous session or start fresh
- [x] Upload skips Gemini processing if duplicates exist; only processes when user explicitly picks "Start fresh"
- [x] Recent papers list on the upload screen with resume / delete per entry
- [x] PDF saved to disk (`backend/app/data/pdfs/{hash}.pdf`), deduplicated by hash
- [x] Per-paper session numbering: sessions sharing the same PDF get labels (1), (2), (3)…

### Persistence
- [x] Full summary fields (key points, methodology, findings) saved to session store
- [x] Chat history persisted to disk after every message; restored in the UI on session resume
- [x] Illustrations saved to session store after each generation; restored when resuming

### Illustrations
- [x] 5 built-in presets: Pencil Sketch, Key Concept Diagram, Process/Workflow, Infographic, Metaphorical
- [x] Image generation via `nano-banana-pro-preview` (generateContent) → JPEG output
- [x] Resolution picker: 512 / 1K / 2K (default) / 4K
- [x] Aspect ratio picker: 1:1 (default) / 16:9 / 4:3 / 9:16
- [x] Multiple iterations per preset — each run appended as v1, v2, v3…
- [x] Named prompt variants per preset: create / edit / delete, persisted to `backend/app/data/prompt_variants.json`
- [x] Standalone custom prompts (not tied to any preset), persisted alongside variants
- [x] Inline thumbnail preview of latest generation per preset
- [x] Gallery with tab filter by preset, version badge, download button, lightbox

### Chat
- [x] Multi-turn chat panel below the summary, backed by Gemini 2.0 Flash with full paper text as context
- [x] Each answer includes cited verbatim quotes from the paper (or web note if external knowledge used)
- [x] **¶ Sources** inline list per answer showing Paper / Web tagged quotes with real URLs for web sources
- [x] **✦ Illustrate** button on each answer — generates a schematic diagram of the answer and adds it to the gallery
- [x] Illustrate button shows animated loading state while generating

### Stack
- [x] Backend: FastAPI + Python, single `GEMINI_API_KEY`, uvicorn with hot-reload
- [x] Frontend: React + Vite + TypeScript, proxied to backend on port 8000
- [x] Git repo at `github.com/medioman22/paper-assistant`
