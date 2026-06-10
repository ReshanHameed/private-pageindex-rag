import type { TreeNode } from '@/lib/types';

interface ForceNode {
  x?: number;
  y?: number;
  id: string;
  data: TreeNode;
  radius: number;
}

interface GraphNodeProps {
  node: ForceNode;
  isSelected?: boolean;
  isInspectTree?: boolean;
  isActivated?: boolean;
  isFetched?: boolean;
  isStreaming?: boolean;
  onClick?: () => void;
}

export default function GraphNode({
  node,
  isSelected,
  isActivated,
  isFetched,
  isStreaming,
  onClick,
}: GraphNodeProps) {
  // Only render if x and y are computed
  if (node.x === undefined || node.y === undefined) return null;

  const isParent = node.data.nodes && node.data.nodes.length > 0;

  // Determine circle classes & stroke width based on live SSE events (animations and hovers disabled per user request)
  let circleClass = '';
  let strokeWidth = 2;

  if (isFetched) {
    // Glowing highlighted state for fetched node. Pulses until next query resets state.
    circleClass += 'fill-accent stroke-accent ';
    if (isStreaming) circleClass += 'animate-trace-pulse ';
    strokeWidth = 2.5;
  } else if (isActivated) {
    // Glowing state for activated/path node (currently being retrieved)
    circleClass += 'fill-accent-ghost stroke-accent ';
    if (isStreaming) circleClass += 'animate-trace-pulse ';
    strokeWidth = 2.5;
  } else if (isSelected) {
    // Static selected node (manual click or citation jump)
    circleClass += 'fill-accent stroke-accent ';
    strokeWidth = 3;
  } else if (isParent) {
    circleClass += 'fill-bg-surface stroke-text-secondary ';
  } else {
    circleClass += 'fill-bg-interactive stroke-border-dim ';
  }
  
  return (
    <g 
      className="group outline-none"
      transform={`translate(${node.x},${node.y})`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`${node.data.title} (pages ${node.data.start_page}-${node.data.end_page})`}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.(); } }}
    >
      {/* Invisible hit area for easier clicking */}
      <circle r={node.radius + 4} fill="transparent" stroke="none" />

      <g className="graph-node-inner">
        {/* Page range badge when activated or fetched */}
        {(isActivated || isFetched) && (
          <text
            y={-(node.radius + 8)}
            className="text-[10px] font-mono fill-accent font-bold pointer-events-none select-none"
            textAnchor="middle"
          >
            p.{node.data.start_page === node.data.end_page ? node.data.start_page : `${node.data.start_page}-${node.data.end_page}`}
          </text>
        )}
        <circle
          r={node.radius}
          className={circleClass}
          strokeWidth={strokeWidth}
        />
        {/* Label text */}
        <text
          y={node.radius + 12}
          className={`
            text-[12px] font-mono pointer-events-none select-none
            ${isSelected ? 'fill-accent font-bold text-sm' : 'fill-text-secondary'}
          `}
          textAnchor="middle"
        >
          {node.data.title.length > 25 ? node.data.title.substring(0, 25) + '…' : node.data.title}
        </text>
      </g>

      {/* Native tooltip for full title */}
      <title>{node.data.title} (pages {node.data.start_page}-{node.data.end_page})</title>
    </g>
  );
}
