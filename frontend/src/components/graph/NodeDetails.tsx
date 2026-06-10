import type { TreeNode } from '@/lib/types';
import { FileText, X } from 'lucide-react';

interface NodeDetailsProps {
  node: TreeNode | null;
  onClose: () => void;
}

export default function NodeDetails({ node, onClose }: NodeDetailsProps) {
  if (!node) return null;

  return (
    <div className="absolute top-4 right-4 w-72 bg-bg-surface border border-border-default border-t-2 border-t-accent/50 shadow-xl flex flex-col animate-fade-in z-10">
      <div className="flex items-center justify-between p-2 border-b border-border-dim bg-bg-void/60">
        <span className="font-mono text-xs font-bold text-text-secondary flex items-center gap-2 uppercase truncate pr-2">
          <FileText className="w-3 h-3 text-accent" /> {node.node_id || 'NODE'}
        </span>
        <button 
          onClick={onClose}
          className="p-1 text-text-tertiary hover:text-text-primary hover:bg-bg-interactive transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      
      <div className="p-3 flex flex-col gap-3 max-h-[60vh] overflow-y-auto custom-scrollbar">
        <div>
          <h4 className="font-mono text-[10px] text-text-tertiary uppercase mb-1">Title</h4>
          <p className="text-sm font-sans font-medium text-text-primary leading-tight">
            {node.title}
          </p>
        </div>
        
        <div>
          <h4 className="font-mono text-[10px] text-text-tertiary uppercase mb-1">Pages</h4>
          <p className="text-xs font-mono bg-bg-interactive inline-block px-1.5 py-0.5 text-text-secondary">
            {node.start_page === node.end_page 
              ? `Page ${node.start_page}` 
              : `Pages ${node.start_page} - ${node.end_page}`}
          </p>
        </div>
        
        {node.summary && (
          <div>
            <h4 className="font-mono text-[10px] text-text-tertiary uppercase mb-1">Summary</h4>
            <p className="text-xs font-sans text-text-secondary leading-relaxed">
              {node.summary}
            </p>
          </div>
        )}

        {node.flags && Object.keys(node.flags).length > 0 && (
          <div>
            <h4 className="font-mono text-[10px] text-text-tertiary uppercase mb-1">Flags</h4>
            <div className="flex flex-wrap gap-1">
              {Object.keys(node.flags).map(key => (
                <span key={key} className="text-[9px] font-mono uppercase bg-accent-ghost text-accent border border-accent/20 px-1 py-0.5">
                  {key}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
