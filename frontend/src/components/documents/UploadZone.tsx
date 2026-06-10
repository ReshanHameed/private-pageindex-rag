import React, { useRef, useState } from 'react';
import { Upload, FileText, X, Play } from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { toast } from 'sonner';

export default function UploadZone() {
  const uploadDocument = useAppStore((state) => state.uploadDocument);
  const [isDragActive, setIsDragActive] = useState(false);
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndStage = (file: File) => {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF files are supported!');
      return;
    }
    setStagedFile(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndStage(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndStage(e.target.files[0]);
    }
    // Reset input so re-selecting the same file triggers onChange again
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleIndex = async () => {
    if (!stagedFile || isUploading) return;
    setIsUploading(true);
    try {
      await uploadDocument(stagedFile);
      setStagedFile(null);
    } catch {
      // Store handles displaying toasts
    } finally {
      setIsUploading(false);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setStagedFile(null);
  };

  const onDropZoneClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!stagedFile) {
      fileInputRef.current?.click();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!stagedFile) {
        fileInputRef.current?.click();
      }
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // --- Staged file view: shows file info + Index button ---
  if (stagedFile) {
    return (
      <div className="border border-dashed border-accent bg-accent-ghost p-6 flex flex-col gap-4 min-h-[180px]">
        {/* Staged file info */}
        <div className="flex items-center gap-3">
          <div className="size-10 bg-bg-interactive border border-border-default flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-accent" />
          </div>
          <div className="flex-1 min-w-0 flex flex-col gap-0.5">
            <span className="font-mono text-sm text-text-primary font-bold truncate">
              {stagedFile.name}
            </span>
            <span className="font-mono text-[10px] text-text-tertiary">
              {formatFileSize(stagedFile.size)} // PDF STAGED
            </span>
          </div>
          <button
            onClick={handleClear}
            disabled={isUploading}
            className="size-8 flex items-center justify-center border border-border-dim text-text-tertiary hover:text-error hover:border-error transition-colors duration-200 disabled:opacity-50 cursor-pointer"
            aria-label="Remove staged file"
            title="Remove"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Index button */}
        <button
          onClick={handleIndex}
          disabled={isUploading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-accent text-text-inverse font-mono text-sm font-bold uppercase tracking-wider hover:bg-accent-dim active:translate-y-[1px] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
        >
          {isUploading ? (
            <>
              <span className="skeleton-shimmer inline-block w-4 h-4" />
              UPLOADING...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              INDEX DOCUMENT
            </>
          )}
        </button>

        <span className="font-mono text-[10px] text-text-tertiary text-center">
          CLICK INDEX TO BEGIN PROCESSING // DROP ANOTHER FILE TO REPLACE
        </span>

        {/* Hidden input + drag overlay for replacing file while staged */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,application/pdf"
          onChange={handleChange}
        />
      </div>
    );
  }

  // --- Default drop zone view ---
  return (
    <div
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      onClick={onDropZoneClick}
      onKeyDown={onKeyDown}
      role="button"
      tabIndex={0}
      aria-label="Upload PDF document"
      className={`border border-dashed transition-all duration-200 cursor-pointer p-8 flex flex-col items-center justify-center gap-4 text-center select-none group min-h-[180px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${
        isDragActive
          ? 'border-accent bg-accent-ghost'
          : 'border-border-bright bg-bg-surface/50 hover:bg-bg-interactive/40'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,application/pdf"
        onChange={handleChange}
      />
      <div className="size-12 bg-bg-interactive border border-border-default group-hover:border-accent group-hover:bg-accent/10 transition-all duration-300 flex items-center justify-center">
        <Upload className="w-6 h-6 text-text-secondary group-hover:text-accent transition-colors duration-300" />
      </div>
      <div className="flex flex-col gap-1 font-mono">
        <span className="text-sm font-bold text-text-primary group-hover:text-accent transition-colors duration-300">
          DRAG & DROP PDF OR CLICK TO CHOOSE
        </span>
        <span className="text-[10px] text-text-tertiary">
          SELECTABLE-TEXT PDFS ONLY // MAX 100MB
        </span>
      </div>
    </div>
  );
}
