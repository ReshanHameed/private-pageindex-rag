
import { ZoomIn, ZoomOut, Maximize, Network } from 'lucide-react';

interface GraphControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onReset?: () => void;
}

export default function GraphControls({ onZoomIn, onZoomOut, onReset }: GraphControlsProps) {
  return (
    <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-bg-surface border border-border-dim p-1 select-none" role="toolbar" aria-label="Graph controls">
      <button 
        onClick={onZoomIn}
        className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-bg-interactive active:translate-y-px transition-all cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        aria-label="Zoom in"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button 
        onClick={onZoomOut}
        className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-bg-interactive active:translate-y-px transition-all cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        aria-label="Zoom out"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <div className="w-px h-4 bg-border-dim mx-1" role="separator" />
      <button 
        onClick={onReset}
        className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-bg-interactive active:translate-y-px transition-all cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        aria-label="Reset graph layout"
      >
        <Maximize className="w-4 h-4" />
      </button>
      <div className="w-px h-4 bg-border-dim mx-1" role="separator" />
      <span className="text-[10px] font-mono text-text-tertiary px-2 flex items-center gap-1">
        <Network className="w-3 h-3" />
        D3_FORCE
      </span>
    </div>
  );
}
