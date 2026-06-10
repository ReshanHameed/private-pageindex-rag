interface CitationLinkProps {
  pageNumber: number;
  onClick?: () => void;
}

/**
 * Interactive citation badge that highlights the corresponding
 * graph node when clicked.
 */
export default function CitationLink({ pageNumber, onClick }: CitationLinkProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-0.5 font-mono text-[11px] text-accent 
                 bg-accent-ghost border border-accent/20 px-1 py-0 mx-0.5 
                 hover:bg-accent/20 hover:border-accent/40 transition-colors 
                 cursor-pointer align-baseline"
      title={`Jump to page ${pageNumber} in graph`}
    >
      [page {pageNumber}]
    </button>
  );
}
