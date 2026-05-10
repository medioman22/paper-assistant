# Paper Assistant — TODO

## Backlog

- [ ] Allow creating custom prompts unrelated from the presets, they should persist across sessions
- [ ] Cache previous sessions so the user can reload a past paper without re-uploading. you should also save and cache papers: so if a paper is uploaded more then once the app should recommend openining one of the previous sessions
- [ ] Commit and push to my GitHub

---

## Done

### Core pipeline
- [x] PDF upload → Gemini 2.0 Flash extracts full text + structured summary (title, abstract, key points, methodology, findings)
- [x] Session ID returned on upload; full paper text stored server-side for chat context

### Illustrations
- [x] 5 built-in presets: Pencil Sketch, Key Concept Diagram, Process/Workflow, Infographic, Metaphorical
- [x] Image generation via `nano-banana-pro-preview` (generateContent) → JPEG output
- [x] Resolution picker: 512 / 1K / 2K (default) / 4K
- [x] Aspect ratio picker: 1:1 (default) / 16:9 / 4:3 / 9:16
- [x] Multiple iterations per preset — each run appended as v1, v2, v3…
- [x] Named prompt variants: create / edit / delete custom prompt templates alongside presets, persisted to `backend/app/data/prompt_variants.json`
- [x] Inline thumbnail preview of latest generation per preset
- [x] Gallery with tab filter by preset, version badge, download button, lightbox

### Chat
- [x] Multi-turn chat panel below the summary, backed by Gemini 2.0 Flash with full paper text as context
- [x] Each answer includes cited verbatim quotes from the paper (or web note if external knowledge used)
- [x] **¶ Sources** popover per answer showing Paper / Web tagged quotes
- [x] **✏️ Illustrate** button on each answer — generates a Pencil Sketch from the answer context and scrolls to the illustration panel

### Stack
- [x] Backend: FastAPI + Python, single `GEMINI_API_KEY`, uvicorn with hot-reload
- [x] Frontend: React + Vite + TypeScript, proxied to backend on port 8000
