import { PaperSummary as Summary } from "../types";

interface Props {
  summary: Summary;
}

export function PaperSummaryPanel({ summary }: Props) {
  return (
    <div className="summary-panel">
      <h2 className="paper-title">{summary.title}</h2>

      <section className="summary-section">
        <h3>Abstract</h3>
        <p>{summary.abstract}</p>
      </section>

      <section className="summary-section">
        <h3>Key Points</h3>
        <ul>
          {summary.key_points.map((pt, i) => (
            <li key={i}>{pt}</li>
          ))}
        </ul>
      </section>

      <div className="summary-grid">
        <section className="summary-section">
          <h3>Methodology</h3>
          <p>{summary.methodology}</p>
        </section>
        <section className="summary-section">
          <h3>Findings</h3>
          <p>{summary.findings}</p>
        </section>
      </div>
    </div>
  );
}
