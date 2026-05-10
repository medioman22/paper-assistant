import { useState, useEffect } from "react";
import { Preset, PromptVariant, IllustrationResult, PresetType, AspectRatio, Resolution } from "../types";
import { generateIllustration, fetchVariants, createVariant, updateVariant, deleteVariant } from "../hooks/useApi";

const PRESET_ICONS: Record<PresetType, string> = {
  sketch: "✏️", key_concept: "🔬", process_workflow: "🔄", infographic: "📊", metaphorical: "🎨",
};
const ASPECT_RATIOS: AspectRatio[] = ["1:1", "16:9", "4:3", "9:16"];
const RESOLUTIONS: { value: Resolution; label: string }[] = [
  { value: "512", label: "512" }, { value: "1024", label: "1K" },
  { value: "2048", label: "2K" }, { value: "4096", label: "4K" },
];

interface Props {
  presets: Preset[];
  paperContext: string;
  illustrations: IllustrationResult[];
  aspectRatio: AspectRatio;
  resolution: Resolution;
  sessionId?: string;
  onAspectRatioChange: (v: AspectRatio) => void;
  onResolutionChange: (v: Resolution) => void;
  onNewResult: (r: IllustrationResult) => void;
}

interface Editor {
  mode: "new" | "edit";
  presetType: PresetType | null; // null = standalone custom
  name: string;
  template: string;
  variantId?: string;
}

export function IllustrationPanel({
  presets, paperContext, illustrations,
  aspectRatio, resolution, sessionId,
  onAspectRatioChange, onResolutionChange,
  onNewResult,
}: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [variants, setVariants] = useState<PromptVariant[]>([]);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchVariants().then(setVariants).catch(() => {}); }, []);

  function nextIteration(preset: PresetType) {
    const existing = illustrations.filter((r) => r.preset === preset);
    return existing.length === 0 ? 1 : Math.max(...existing.map((r) => r.iteration)) + 1;
  }

  function latestFor(preset: PresetType) {
    const all = illustrations.filter((r) => r.preset === preset);
    return all.length ? all.reduce((a, b) => (a.iteration > b.iteration ? a : b)) : null;
  }

  async function handleGenerate(preset: PresetType, variantId?: string) {
    const key = variantId ?? preset;
    setLoading(key);
    setErrors((e) => ({ ...e, [key]: "" }));
    try {
      const result = await generateIllustration({
        preset,
        paper_context: paperContext,
        aspect_ratio: aspectRatio,
        resolution,
        iteration: nextIteration(preset),
        variant_id: variantId,
        session_id: sessionId,
      });
      onNewResult(result);
    } catch (err) {
      setErrors((e) => ({ ...e, [key]: String(err) }));
    } finally {
      setLoading(null);
    }
  }

  function openNewEditor(presetType: PresetType | null) {
    const def = presetType ? presets.find((p) => p.id === presetType)?.default_template ?? "" : "";
    setEditor({ mode: "new", presetType, name: "", template: def });
  }

  function openEditEditor(v: PromptVariant) {
    setEditor({ mode: "edit", presetType: v.preset_type ?? null, name: v.name, template: v.template, variantId: v.id });
  }

  async function handleSaveEditor() {
    if (!editor) return;
    setSaving(true);
    try {
      if (editor.mode === "new") {
        const v = await createVariant(editor.name, editor.presetType, editor.template);
        setVariants((prev) => [...prev, v]);
      } else if (editor.variantId) {
        const v = await updateVariant(editor.variantId, editor.name, editor.presetType, editor.template);
        setVariants((prev) => prev.map((x) => (x.id === v.id ? v : x)));
      }
      setEditor(null);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteVariant(id: string) {
    await deleteVariant(id);
    setVariants((prev) => prev.filter((v) => v.id !== id));
  }

  const standaloneVariants = variants.filter((v) => !v.preset_type);

  return (
    <div className="illustration-panel">
      <h2>Illustrations</h2>

      <div className="gen-controls">
        <div className="control-group">
          <label>Aspect ratio</label>
          <div className="pill-group">
            {ASPECT_RATIOS.map((r) => (
              <button key={r} className={`pill ${aspectRatio === r ? "active" : ""}`} onClick={() => onAspectRatioChange(r)}>{r}</button>
            ))}
          </div>
        </div>
        <div className="control-group">
          <label>Resolution</label>
          <div className="pill-group">
            {RESOLUTIONS.map(({ value, label }) => (
              <button key={value} className={`pill ${resolution === value ? "active" : ""}`} onClick={() => onResolutionChange(value)}>{label}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Built-in presets */}
      <div className="preset-grid">
        {presets.map((preset) => {
          const latest = latestFor(preset.id);
          const isLoading = loading === preset.id;
          const presetVariants = variants.filter((v) => v.preset_type === preset.id);

          return (
            <div key={preset.id} className="preset-item">
              {latest && (
                <div className="preset-thumb-wrap">
                  <img
                    className="preset-thumb"
                    src={`data:${latest.mime_type};base64,${latest.image_b64}`}
                    alt={preset.label}
                  />
                  {illustrations.filter((r) => r.preset === preset.id).length > 1 && (
                    <span className="iter-badge">{illustrations.filter((r) => r.preset === preset.id).length} versions</span>
                  )}
                </div>
              )}
              <div className="preset-row">
                <button
                  className={`preset-card ${latest ? "done" : ""} ${isLoading ? "generating" : ""}`}
                  onClick={() => handleGenerate(preset.id)}
                  disabled={!!loading}
                >
                  <span className="preset-icon">{PRESET_ICONS[preset.id]}</span>
                  <span className="preset-label">{preset.label}</span>
                  {isLoading ? <span className="preset-status">Generating…</span>
                    : latest ? <span className="preset-status done-badge">↺</span> : null}
                </button>
                <button className="prompt-edit-btn" onClick={() => openNewEditor(preset.id)} title="New variant">+</button>
              </div>
              {errors[preset.id] && <p className="preset-error">{errors[preset.id]}</p>}
              {presetVariants.map((v) => {
                const vLoading = loading === v.id;
                return (
                  <div key={v.id} className="variant-row">
                    <button
                      className={`variant-card ${vLoading ? "generating" : ""}`}
                      onClick={() => handleGenerate(v.preset_type!, v.id)}
                      disabled={!!loading}
                    >
                      <span className="variant-name">{v.name}</span>
                      {vLoading && <span className="preset-status">Generating…</span>}
                    </button>
                    <button className="variant-action" onClick={() => openEditEditor(v)} title="Edit">✎</button>
                    <button className="variant-action danger" onClick={() => handleDeleteVariant(v.id)} title="Delete">×</button>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Standalone custom prompts */}
      <div className="custom-prompts-section">
        <div className="custom-prompts-header">
          <span className="control-group-label">Custom prompts</span>
          <button className="prompt-edit-btn" onClick={() => openNewEditor(null)} title="New custom prompt">+</button>
        </div>
        {standaloneVariants.length === 0 && !editor && (
          <p className="custom-prompts-empty">No custom prompts yet — create one with +</p>
        )}
        {standaloneVariants.map((v) => {
          const vLoading = loading === v.id;
          return (
            <div key={v.id} className="variant-row">
              <button
                className={`variant-card ${vLoading ? "generating" : ""}`}
                onClick={() => handleGenerate("key_concept", v.id)}
                disabled={!!loading}
              >
                <span className="variant-name">✦ {v.name}</span>
                {vLoading && <span className="preset-status">Generating…</span>}
              </button>
              <button className="variant-action" onClick={() => openEditEditor(v)} title="Edit">✎</button>
              <button className="variant-action danger" onClick={() => handleDeleteVariant(v.id)} title="Delete">×</button>
            </div>
          );
        })}
      </div>

      {/* Variant editor */}
      {editor && (
        <div className="prompt-editor">
          <div className="prompt-editor-header">
            {editor.mode === "new" ? "New" : "Edit"}{editor.presetType ? ` variant — ${presets.find((p) => p.id === editor.presetType)?.label}` : " custom prompt"}
          </div>
          <input
            className="variant-name-input"
            placeholder="Name (e.g. Dark background, Blueprint)"
            value={editor.name}
            onChange={(e) => setEditor({ ...editor, name: e.target.value })}
          />
          <p className="prompt-editor-hint">
            Use <code>{"{context}"}</code> where the paper summary should be inserted.
            {!editor.presetType && " For custom prompts, {context} is optional."}
          </p>
          <textarea
            value={editor.template}
            onChange={(e) => setEditor({ ...editor, template: e.target.value })}
            rows={6}
            spellCheck={false}
          />
          <div className="prompt-editor-actions">
            <button className="btn-primary" onClick={handleSaveEditor} disabled={saving || !editor.name.trim()}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button className="btn-ghost" onClick={() => setEditor(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
