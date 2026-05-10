import { useRef, useState, DragEvent } from "react";

interface Props {
  onUpload: (file: File) => void;
  loading: boolean;
}

export function PaperUpload({ onUpload, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file && file.type === "application/pdf") onUpload(file);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""} ${loading ? "loading" : ""}`}
      onClick={() => !loading && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={(e) => handleFiles(e.target.files)}
      />
      {loading ? (
        <div className="upload-state">
          <div className="spinner" />
          <p>Reading paper…</p>
        </div>
      ) : (
        <div className="upload-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <polyline points="9 15 12 12 15 15" />
          </svg>
          <p><strong>Drop a PDF here</strong> or click to browse</p>
          <span>Academic papers, preprints, research documents</span>
        </div>
      )}
    </div>
  );
}
