import { SessionMeta } from "../types";
import { deleteSession } from "../hooks/useApi";

interface Props {
  sessions: SessionMeta[];
  onResume: (id: string) => void;
  onDeleted: (id: string) => void;
}

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function RecentSessions({ sessions, onResume, onDeleted }: Props) {
  if (sessions.length === 0) return null;

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await deleteSession(id);
    onDeleted(id);
  }

  return (
    <div className="recent-sessions">
      <h3>Recent papers</h3>
      <div className="session-list">
        {sessions.map((s) => (
          <div key={s.session_id} className="session-card" onClick={() => onResume(s.session_id)}>
            <div className="session-info">
              <span className="session-title">{s.title}</span>
              <span className="session-date">{fmt(s.created_at)}</span>
            </div>
            <button
              className="session-delete"
              onClick={(e) => handleDelete(s.session_id, e)}
              title="Remove"
            >×</button>
          </div>
        ))}
      </div>
    </div>
  );
}

interface DuplicateBannerProps {
  duplicates: SessionMeta[];
  onResume: (id: string) => void;
  onDismiss: () => void;
}

export function DuplicateBanner({ duplicates, onResume, onDismiss }: DuplicateBannerProps) {
  return (
    <div className="duplicate-banner">
      <span>This paper was already analyzed</span>
      <div className="duplicate-actions">
        {duplicates.map((s) => (
          <button key={s.session_id} className="btn-primary" onClick={() => onResume(s.session_id)}>
            Open {new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </button>
        ))}
        <button className="btn-ghost" onClick={onDismiss}>Start fresh</button>
      </div>
    </div>
  );
}
