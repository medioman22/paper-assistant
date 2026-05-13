import { useEffect, useCallback, useState } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  Node, Edge, NodeProps, Handle, Position,
  useNodesState, useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { LiteratureGraph, GraphNode, GraphEdge, RelationshipType } from "../types";
import { fetchLiteratureGraph } from "../hooks/useApi";

// ── Colours ──────────────────────────────────────────────────────────────────

const REL_COLOR: Record<string, string> = {
  cited:       "#6c8ebf",
  foundational:"#d4a017",
  parallel:    "#5a9e6f",
  subsequent:  "#9673a6",
  related:     "#888888",
};
const ROOT_COLOR = "#6c63ff";

// ── Tree layout ───────────────────────────────────────────────────────────────

const NODE_W = 200;
const NODE_H = 72;
const H_GAP  = 48;
const V_GAP  = 100;

function buildTreeLayout(graphNodes: GraphNode[], graphEdges: GraphEdge[]) {
  // Enforce single-parent: first edge wins
  const childrenOf = new Map<string, string[]>(graphNodes.map(n => [n.id, []]));
  const parentOf   = new Map<string, string>();
  const edgeRelOf  = new Map<string, string>(); // nodeId → relationship from parent

  for (const e of graphEdges) {
    if (!parentOf.has(e.target)) {
      parentOf.set(e.target, e.source);
      edgeRelOf.set(e.target, e.relationship);
      const kids = childrenOf.get(e.source);
      if (kids) kids.push(e.target);
    }
  }

  const roots = graphNodes.filter(n => !parentOf.has(n.id));

  function subtreeWidth(id: string): number {
    const kids = childrenOf.get(id) ?? [];
    if (!kids.length) return NODE_W;
    const total = kids.reduce((s, k) => s + subtreeWidth(k), 0) + H_GAP * (kids.length - 1);
    return Math.max(NODE_W, total);
  }

  const positions = new Map<string, { x: number; y: number }>();

  function place(id: string, cx: number, y: number) {
    positions.set(id, { x: cx - NODE_W / 2, y });
    const kids = childrenOf.get(id) ?? [];
    if (!kids.length) return;
    const total = kids.reduce((s, k) => s + subtreeWidth(k), 0) + H_GAP * (kids.length - 1);
    let x = cx - total / 2;
    for (const kid of kids) {
      const w = subtreeWidth(kid);
      place(kid, x + w / 2, y + NODE_H + V_GAP);
      x += w + H_GAP;
    }
  }

  let rx = 0;
  for (const root of roots) {
    const w = subtreeWidth(root.id);
    place(root.id, rx + w / 2, 0);
    rx += w + H_GAP * 3;
  }

  return { positions, parentOf, edgeRelOf };
}

// ── Node component ────────────────────────────────────────────────────────────

function PaperNodeComponent({ data }: NodeProps) {
  const d = data as Record<string, unknown>;
  const [hovered, setHovered] = useState(false);

  const title     = d.title as string;
  const year      = d.year as string | undefined;
  const authors   = d.authors as string | undefined;
  const firstAuthor = authors ? authors.split(/[,;]/)[0].trim() : "";
  const preview   = (d.abstract || d.takeaway) as string | undefined;
  const sessionId = d.session_id as string | null | undefined;
  const url       = d.url as string | undefined;
  const color     = d.color as string;
  const onOpen    = d.onOpen as (() => void) | undefined;
  const onFetch   = d.onFetch as (() => void) | undefined;

  return (
    <div
      className="flow-node"
      style={{ borderColor: color }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />

      <div className="flow-node-title" title={title}>{title}</div>
      <div className="flow-node-meta">
        {firstAuthor && <span>{firstAuthor}</span>}
        {firstAuthor && year && <span className="flow-node-sep">·</span>}
        {year && <span>{year}</span>}
      </div>

      <div className="flow-node-actions">
        {sessionId && onOpen && (
          <button className="flow-node-btn" style={{ color }} onClick={onOpen}>Open →</button>
        )}
        {!sessionId && url && (
          <>
            <a className="flow-node-btn" style={{ color }} href={url} target="_blank" rel="noreferrer">↗ Link</a>
            {onFetch && <><span className="flow-node-sep">·</span><button className="flow-node-btn" style={{ color }} onClick={onFetch}>⬇ Fetch</button></>}
          </>
        )}
      </div>

      {hovered && preview && (
        <div className="flow-node-tooltip">{preview}</div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  );
}

const nodeTypes = { paper: PaperNodeComponent };

// ── Graph → React Flow conversion ─────────────────────────────────────────────

function toFlowElements(
  graphData: LiteratureGraph,
  onOpenSession: (id: string) => void,
  onFetchPaper: (url: string, title?: string) => void,
): { nodes: Node[]; edges: Edge[] } {
  const { positions, parentOf, edgeRelOf } = buildTreeLayout(graphData.nodes, graphData.edges);

  const nodes: Node[] = graphData.nodes.map(n => {
    const rel  = edgeRelOf.get(n.id);
    const color = n.session_id ? ROOT_COLOR : (rel ? REL_COLOR[rel] ?? REL_COLOR.related : REL_COLOR.related);
    return {
      id:       n.id,
      type:     "paper",
      position: positions.get(n.id) ?? { x: 0, y: 0 },
      data: {
        ...n,
        color,
        onOpen:  n.session_id ? () => onOpenSession(n.session_id!) : undefined,
        onFetch: !n.session_id && n.url ? () => onFetchPaper(n.url!, n.title) : undefined,
      },
    };
  });

  const edges: Edge[] = graphData.edges
    .filter(e => parentOf.get(e.target) === e.source) // only canonical parent edge
    .map(e => {
      const color = REL_COLOR[e.relationship] ?? REL_COLOR.related;
      return {
        id:         e.id,
        source:     e.source,
        target:     e.target,
        label:      e.relationship as RelationshipType,
        style:      { stroke: color, strokeWidth: 2 },
        labelStyle: { fontSize: 10, fill: color },
        labelBgStyle: { fill: "#1a1a2e", fillOpacity: 0.85 },
      };
    });

  return { nodes, edges };
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  revision?: number;
  onClose: () => void;
  onOpenSession: (sessionId: string) => void;
  onFetchPaper: (url: string, title?: string) => void;
}

export function LiteratureMap({ revision = 0, onClose, onOpenSession, onFetchPaper }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const load = useCallback(async () => {
    try {
      const graph = await fetchLiteratureGraph();
      const { nodes: n, edges: e } = toFlowElements(graph, onOpenSession, onFetchPaper);
      setNodes(n);
      setEdges(e);
    } catch { /* empty graph is fine */ }
  }, [onOpenSession, onFetchPaper, setNodes, setEdges]);

  useEffect(() => { load(); }, [load, revision]);

  return (
    <div className="literature-map-overlay">
      <div className="literature-map-header">
        <h2>Literature Map</h2>
        <div className="lit-legend">
          <span className="lit-legend-item">
            <span className="lit-legend-dot" style={{ background: ROOT_COLOR }} />
            analyzed
          </span>
          {Object.entries(REL_COLOR).map(([rel, color]) => (
            <span key={rel} className="lit-legend-item">
              <span className="lit-legend-dot" style={{ background: color }} />
              {rel}
            </span>
          ))}
        </div>
        <button className="btn-ghost" onClick={onClose}>✕ Close</button>
      </div>

      {nodes.length === 0 ? (
        <div className="literature-map-empty">
          <p>No papers in the literature graph yet.</p>
          <p>Open a paper and click "Find related papers" to start building the map.</p>
        </div>
      ) : (
        <div className="literature-map-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.15 }}
          >
            <Background color="#2a2a3e" gap={24} />
            <Controls />
            <MiniMap
              nodeColor={(n) => (n.data?.color as string) ?? "#444"}
              maskColor="rgba(20,20,40,0.6)"
            />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
