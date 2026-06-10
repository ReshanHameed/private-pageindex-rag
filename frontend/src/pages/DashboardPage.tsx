import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Trash2, Check, AlertCircle, RefreshCw, Terminal, ArrowRight } from 'lucide-react';
import { useAppStore } from '../lib/store';
import UploadZone from '../components/documents/UploadZone';
import ProgressBar from '../components/documents/ProgressBar';
import ElapsedTimer from '../components/documents/ElapsedTimer';

export default function DashboardPage() {
  const { documents, loading, error, fetchDocuments, deleteDocument } = useAppStore();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return (
    <div className="flex flex-col gap-8 w-full h-full overflow-y-auto animate-fade-in pb-12 pr-2">
      
      {/* Introduction Banner */}
      <div className="flex flex-col gap-2 border border-border-default bg-bg-surface p-6">
        <h2 className="text-xl font-display font-bold text-accent tracking-tight flex items-center gap-2">
          <Terminal className="w-5 h-5 text-accent" /> LOCAL WORKSPACE CONSOLE
        </h2>
        <p className="text-sm text-text-secondary max-w-[75ch] leading-relaxed">
          Welcome to your local document intelligence environment. Upload a text-searchable PDF below to ingest, detect outline headings, and build a spatial knowledge graph for targeted LLM retrieval.
        </p>
      </div>

      {/* Upload Zone */}
      <UploadZone />

      {/* Documents Grid Section */}
      <div className="flex flex-col gap-4">
        <div className="flex justify-between items-center border-b border-border-dim pb-2 select-none">
          <span className="font-mono text-xs font-bold text-text-secondary flex items-center gap-2">
            INDEXED_FILES_CATALOG ({documents.length})
          </span>
          <span className="font-mono text-[10px] text-text-tertiary">
            SORTED_BY: ROWID_DESC
          </span>
        </div>

        {error && (
          <div className="border border-error/50 bg-error-ghost/10 p-4 font-mono text-xs text-error flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-error" />
            <span>ERROR FETCHING DOCUMENTS: {error}</span>
          </div>
        )}

        {loading && documents.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="border border-border-dim p-4 bg-bg-surface flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2.5 w-2/3">
                    <div className="size-5 skeleton-shimmer" />
                    <div className="flex-1 flex flex-col gap-1.5">
                      <div className="h-4 skeleton-shimmer w-full" />
                      <div className="h-3 skeleton-shimmer w-1/2" />
                    </div>
                  </div>
                </div>
                <div className="h-8 skeleton-shimmer w-full mt-2" />
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="border border-dashed border-border-default p-12 text-center flex flex-col items-center gap-4 select-none">
            <Terminal className="w-8 h-8 text-text-tertiary" />
            <div className="flex flex-col gap-1">
              <span className="font-display font-medium text-sm text-text-secondary">No documents indexed</span>
              <span className="font-mono text-[10px] text-text-tertiary">Upload a text-searchable PDF above to begin indexing</span>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => {
              const isOptimistic = doc.id.startsWith('temp-');
              
              return (
                <div
                  key={doc.id}
                  className={`border p-4 bg-bg-surface flex flex-col justify-between gap-3 group relative transition-all duration-300 ${
                    doc.status === 'completed'
                      ? 'border-border-dim hover:border-border-bright'
                      : doc.status === 'processing'
                      ? 'border-warning/60 hover:border-warning'
                      : 'border-error/40 hover:border-error'
                  }`}
                >
                  <div>
                    {/* Document Title & Delete */}
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex items-start gap-2.5">
                        <FileText
                          className={`w-5 h-5 mt-0.5 ${
                            doc.status === 'completed'
                              ? 'text-accent'
                              : doc.status === 'processing'
                              ? 'text-warning animate-pulse'
                              : 'text-error'
                          }`}
                        />
                        <div className="flex flex-col">
                          {doc.status === 'completed' ? (
                            <Link
                              to={`/documents/${doc.id}`}
                              className="font-display font-medium text-sm text-text-primary hover:text-accent cursor-pointer line-clamp-1 transition-colors duration-200"
                            >
                              {doc.filename}
                            </Link>
                          ) : (
                            <span className="font-display font-medium text-sm text-text-primary line-clamp-1">
                              {doc.filename}
                            </span>
                          )}
                          <span className="font-mono text-[10px] text-text-tertiary">
                            {isOptimistic ? (
                              <span>UPLOADING TO DB...</span>
                            ) : (
                              <span>
                                ID: {doc.id.slice(0, 8)}... · {new Date(doc.created_at).toLocaleDateString()}
                              </span>
                            )}
                          </span>
                        </div>
                      </div>

                      {!isOptimistic && (
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeletingId(doc.id); }}
                          className="text-text-tertiary hover:text-error hover:bg-bg-interactive border border-transparent hover:border-border-dim p-1 transition-colors duration-200 cursor-pointer"
                          title="Purge document data"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress and status details */}
                  <div className="mt-2 font-mono text-xs flex flex-col gap-2">
                    {doc.status === 'completed' && deletingId !== doc.id && (
                      <div className="flex items-center justify-between text-text-secondary bg-bg-void px-3 py-1.5 border border-border-dim">
                        <span className="flex items-center gap-1.5 text-success font-bold text-[10px] tracking-wider">
                          <Check className="w-3.5 h-3.5" /> READY
                        </span>
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-text-tertiary">
                            {doc.page_count} PAGES · {doc.elapsed_seconds}s
                          </span>
                          <Link
                            to={`/documents/${doc.id}`}
                            className="text-[10px] text-accent flex items-center gap-0.5 hover:underline font-bold"
                          >
                            OPEN <ArrowRight className="w-3 h-3" />
                          </Link>
                        </div>
                      </div>
                    )}

                    {doc.status === 'processing' && deletingId !== doc.id && (
                      <div className="flex items-center gap-3 bg-bg-void px-3 py-2 border border-warning/30">
                        {/* Progress Bar */}
                        <div className="shrink-0 flex items-center">
                          <ProgressBar value={doc.progress_percent} />
                        </div>
                        
                        <div className="flex-1 min-w-0 flex items-center gap-1.5 font-bold uppercase animate-pulse text-[10px] text-warning truncate">
                          <span className="text-text-tertiary px-1 shrink-0">·</span>
                          <RefreshCw className="w-3 h-3 animate-spin shrink-0" /> 
                          <span className="truncate">{doc.progress_stage || 'processing'}...</span>
                        </div>

                        {!isOptimistic && (
                          <div className="ml-auto text-[10px] text-warning">
                            <ElapsedTimer startedAt={doc.created_at} finishedAt={null} />
                          </div>
                        )}
                      </div>
                    )}

                    {doc.status === 'failed' && deletingId !== doc.id && (
                      <div className="flex flex-col gap-1 bg-bg-void px-3 py-2 border border-error/20 text-error">
                        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase">
                          <AlertCircle className="w-3.5 h-3.5" /> INDEXING_FAILED
                        </span>
                        <p className="text-[10px] text-text-secondary leading-normal line-clamp-2">
                          {doc.error}
                        </p>
                      </div>
                    )}

                    {/* Inline delete confirmation bar */}
                    {deletingId === doc.id && (
                      <div className="flex items-center justify-between bg-bg-void border border-error/30 px-3 py-1.5">
                        <span className="font-mono text-[10px] text-error uppercase">CONFIRM_DELETE?</span>
                        <div className="flex items-center gap-2">
                          <button onClick={() => setDeletingId(null)} className="font-mono text-[10px] text-text-secondary hover:text-text-primary border border-border-dim px-2 py-0.5 cursor-pointer transition-colors">
                            CANCEL
                          </button>
                          <button onClick={() => { deleteDocument(doc.id); setDeletingId(null); }} className="font-mono text-[10px] text-bg-void bg-error hover:bg-error/80 px-2 py-0.5 font-bold cursor-pointer transition-colors">
                            PURGE
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
