import { useAppStore } from '../../lib/store';

export default function OllamaStatus() {
  const { ollamaStatus, fetchOllamaStatusAndModels } = useAppStore();

  const statusTitle =
    ollamaStatus === 'connected'
      ? 'Ollama is running and reachable at localhost:11434'
      : ollamaStatus === 'checking' || ollamaStatus === null
        ? 'Checking Ollama connection status...'
        : 'Ollama is not reachable. Click to retry.';

  return (
    <button
      onClick={() => fetchOllamaStatusAndModels()}
      className="flex items-center gap-2 border border-border-dim bg-bg-void px-3 py-1 font-mono text-xs hover:border-border-bright hover:bg-bg-interactive transition-colors duration-200 cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      title={statusTitle}
    >
      <span className="text-text-tertiary select-none">STATUS:</span>
      {ollamaStatus === 'checking' || ollamaStatus === null ? (
        <span className="text-warning flex items-center gap-1.5">
          <span className="font-mono text-[8px] animate-pulse">●</span> CHECKING
        </span>
      ) : ollamaStatus === 'connected' ? (
        <span className="text-success flex items-center gap-1.5 font-bold">
          <span className="font-mono text-[8px]">●</span> CONNECTED
        </span>
      ) : (
        <span className="text-error flex items-center gap-1.5 font-bold">
          <span className="font-mono text-[8px]">○</span> OFFLINE
        </span>
      )}
    </button>
  );
}
