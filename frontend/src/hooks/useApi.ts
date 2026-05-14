import {
  UploadResponse, Preset, IllustrationResult, GenerateRequest,
  PromptVariant, ChatMessage, PresetType, SessionMeta, PaperSummary,
  PaperRecommendation, LiteratureGraph,
} from "../types";

const BASE = "";

export async function uploadPaper(file: File, force = false): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("force", String(force));
  const res = await fetch(`${BASE}/papers/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

export async function fetchPresets(): Promise<Preset[]> {
  const res = await fetch(`${BASE}/illustrations/presets`);
  if (!res.ok) throw new Error("Could not load presets");
  return res.json();
}

export async function generateIllustration(req: GenerateRequest): Promise<IllustrationResult> {
  const res = await fetch(`${BASE}/illustrations/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Generation failed");
  }
  return res.json();
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export async function fetchSessions(): Promise<SessionMeta[]> {
  const res = await fetch(`${BASE}/papers/sessions`);
  if (!res.ok) return [];
  return res.json();
}

export async function resumeSession(sessionId: string): Promise<{ session_id: string; summary: PaperSummary; created_at: string; illustrations: IllustrationResult[]; chat_history: { question: string; answer: string; sources: ChatMessage["sources"] }[] }> {
  const res = await fetch(`${BASE}/papers/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/papers/sessions/${sessionId}`, { method: "DELETE" });
}

// ── Variants ─────────────────────────────────────────────────────────────────

export async function fetchVariants(): Promise<PromptVariant[]> {
  const res = await fetch(`${BASE}/illustrations/variants`);
  if (!res.ok) throw new Error("Could not load variants");
  return res.json();
}

export async function createVariant(
  name: string, preset_type: PresetType | null, template: string
): Promise<PromptVariant> {
  const res = await fetch(`${BASE}/illustrations/variants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, preset_type, template }),
  });
  if (!res.ok) throw new Error("Could not save variant");
  return res.json();
}

export async function updateVariant(
  id: string, name: string, preset_type: PresetType | null, template: string
): Promise<PromptVariant> {
  const res = await fetch(`${BASE}/illustrations/variants/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, preset_type, template }),
  });
  if (!res.ok) throw new Error("Could not update variant");
  return res.json();
}

export async function deleteVariant(id: string): Promise<void> {
  await fetch(`${BASE}/illustrations/variants/${id}`, { method: "DELETE" });
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function askQuestion(
  sessionId: string, question: string
): Promise<{ answer: string; sources: ChatMessage["sources"] }> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Chat failed");
  }
  return res.json();
}

// ── Literature ────────────────────────────────────────────────────────────────

export async function fetchLiteratureGraph(): Promise<LiteratureGraph> {
  const res = await fetch(`${BASE}/literature/graph`);
  if (!res.ok) throw new Error("Could not load literature graph");
  return res.json();
}

export async function fetchRecommendations(sessionId: string): Promise<{ recommendations: PaperRecommendation[]; cached: boolean }> {
  const res = await fetch(`${BASE}/literature/recommendations/${sessionId}`);
  if (!res.ok) throw new Error("Could not load recommendations");
  return res.json();
}

export async function generateRecommendations(sessionId: string): Promise<{ recommendations: PaperRecommendation[]; cached: boolean }> {
  const res = await fetch(`${BASE}/literature/recommendations/${sessionId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Recommendation failed");
  }
  return res.json();
}

export async function searchPapers(query: string): Promise<{ results: import("../types").PaperSearchResult[] }> {
  const res = await fetch(`${BASE}/literature/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Search failed");
  }
  return res.json();
}

export async function fetchAndAnalyzePaper(url: string, force = false, title?: string): Promise<UploadResponse> {
  const res = await fetch(`${BASE}/papers/fetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, force, title }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Fetch failed");
  }
  return res.json();
}
