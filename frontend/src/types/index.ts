export type PresetType =
  | "sketch"
  | "key_concept"
  | "process_workflow"
  | "infographic"
  | "metaphorical";

export type AspectRatio = "1:1" | "16:9" | "4:3" | "9:16";
export type Resolution = "512" | "1024" | "2048" | "4096";

export interface PaperSummary {
  title: string;
  abstract: string;
  key_points: string[];
  methodology: string;
  findings: string;
  raw_text_excerpt: string;
}

export interface SessionMeta {
  session_id: string;
  title: string;
  abstract: string;
  created_at: string;
  paper_hash: string;
}

export interface UploadResponse {
  session_id: string;
  summary: PaperSummary;
  duplicate_sessions: SessionMeta[];
}

export interface Preset {
  id: PresetType;
  label: string;
  default_template: string;
}

export interface PromptVariant {
  id: string;
  name: string;
  preset_type: PresetType | null;
  template: string;
}

export interface IllustrationResult {
  preset: PresetType;
  label: string;
  image_b64: string;
  mime_type: string;
  prompt_used: string;
  iteration: number;
  aspect_ratio: AspectRatio;
  resolution: Resolution;
  variant_name: string | null;
}

export interface GenerateRequest {
  preset: PresetType;
  paper_context: string;
  aspect_ratio: AspectRatio;
  resolution: Resolution;
  iteration: number;
  variant_id?: string;
  custom_template?: string;
  session_id?: string;
}

export interface ChatSource {
  type: "paper" | "web";
  quote: string;
  url?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
  context?: string;  // for illustrate action
}
