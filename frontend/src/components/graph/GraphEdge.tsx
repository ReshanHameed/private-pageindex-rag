

interface ForceNode {
  x?: number;
  y?: number;
  id: string;
}

interface GraphEdgeProps {
  source: ForceNode;
  target: ForceNode;
  isActivated?: boolean;
  isFetched?: boolean;
  isSelected?: boolean;
}

export default function GraphEdge({
  source,
  target,
  isActivated = false,
  isFetched = false,
  isSelected = false,
}: GraphEdgeProps) {
  if (source.x === undefined || source.y === undefined || target.x === undefined || target.y === undefined) {
    return null;
  }

  // Determine edge styling based on active retrieval or selection states
  let strokeOpacity = 0.30;
  let strokeWidth = 1.50;

  if (isFetched) {
    strokeOpacity = 1.0;
    strokeWidth = 3.0;
  } else if (isSelected) {
    strokeOpacity = 0.85;
    strokeWidth = 2.50;
  } else if (isActivated) {
    strokeOpacity = 0.55;
    strokeWidth = 2.00;
  }

  return (
    <g>
      <line
        className="graph-edge-inner pointer-events-none transition-[stroke-width,stroke-opacity] duration-300"
        x1={source.x}
        y1={source.y}
        x2={target.x}
        y2={target.y}
        stroke="var(--color-accent)"
        strokeWidth={strokeWidth}
        strokeOpacity={strokeOpacity}
      />
    </g>
  );
}

