import { useState } from "react";
import { IllustrationResult, PresetType } from "../types";

interface Props {
  results: IllustrationResult[];
}

const PRESET_ORDER: PresetType[] = ["sketch", "key_concept", "process_workflow", "infographic", "metaphorical"];

export function ImageGallery({ results }: Props) {
  const [expanded, setExpanded] = useState<IllustrationResult | null>(null);
  const [activePreset, setActivePreset] = useState<PresetType | "all">("all");

  if (results.length === 0) return null;

  const presetTabs = PRESET_ORDER.filter((p) => results.some((r) => r.preset === p));

  const visible =
    activePreset === "all"
      ? results
      : results.filter((r) => r.preset === activePreset);

  function download(r: IllustrationResult) {
    const a = document.createElement("a");
    a.href = `data:${r.mime_type};base64,${r.image_b64}`;
    a.download = `${r.preset}_v${r.iteration}.${r.mime_type.split("/")[1]}`;
    a.click();
  }

  return (
    <div className="gallery">
      <div className="gallery-header">
        <h2>Generated Illustrations</h2>
        <div className="gallery-tabs">
          <button
            className={`gallery-tab ${activePreset === "all" ? "active" : ""}`}
            onClick={() => setActivePreset("all")}
          >
            All ({results.length})
          </button>
          {presetTabs.map((p) => {
            const count = results.filter((r) => r.preset === p).length;
            const label = results.find((r) => r.preset === p)!.label;
            return (
              <button
                key={p}
                className={`gallery-tab ${activePreset === p ? "active" : ""}`}
                onClick={() => setActivePreset(p)}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      <div className="gallery-grid">
        {visible.map((r, i) => (
          <div key={`${r.preset}-${r.iteration}-${i}`} className="gallery-card">
            <div className="gallery-card-img-wrap">
              <img
                src={`data:${r.mime_type};base64,${r.image_b64}`}
                alt={r.label}
                onClick={() => setExpanded(r)}
              />
              <span className="gallery-iter-badge">v{r.iteration}</span>
            </div>
            <div className="gallery-card-footer">
              <div className="gallery-card-meta">
                <span className="gallery-card-label">{r.label}</span>
                <span className="gallery-card-info">{r.resolution}px · {r.aspect_ratio}</span>
              </div>
              <button onClick={() => download(r)} title="Download">↓</button>
            </div>
          </div>
        ))}
      </div>

      {expanded && (
        <div className="lightbox" onClick={() => setExpanded(null)}>
          <div className="lightbox-inner" onClick={(e) => e.stopPropagation()}>
            <img src={`data:${expanded.mime_type};base64,${expanded.image_b64}`} alt={expanded.label} />
            <div className="lightbox-meta">
              <strong>{expanded.label} — v{expanded.iteration}</strong>
              <span className="gallery-card-info">{expanded.resolution}px · {expanded.aspect_ratio}</span>
              <details>
                <summary>Prompt used</summary>
                <p>{expanded.prompt_used}</p>
              </details>
            </div>
            <button className="lightbox-close" onClick={() => setExpanded(null)}>✕</button>
          </div>
        </div>
      )}
    </div>
  );
}
