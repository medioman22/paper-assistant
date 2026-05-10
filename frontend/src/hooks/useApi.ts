import {
  UploadResponse, Preset, IllustrationResult, GenerateRequest,
  PromptVariant, ChatMessage, PresetType, SessionMeta, PaperSummary,
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
