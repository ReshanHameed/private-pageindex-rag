import { Cpu } from 'lucide-react';
import { useAppStore } from '../../lib/store';

export default function ModelPicker() {
  const { selectedModel, ollamaModels, setSelectedModel } = useAppStore();

  return (
    <div className="flex items-center gap-2 border border-border-dim bg-bg-void px-3 py-1 font-mono text-xs transition-colors duration-200 hover:border-border-default">
      <Cpu className="size-3.5 text-text-secondary" />
      <select
        value={selectedModel}
        onChange={(e) => setSelectedModel(e.target.value)}
        className="bg-transparent text-text-secondary hover:text-text-primary transition-colors duration-200 border-none cursor-pointer font-mono focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
        title="Select Ollama model"
      >
        {ollamaModels.map((model) => (
          <option key={model} value={model} className="bg-bg-elevated text-text-primary font-mono">
            ✓ {model}
          </option>
        ))}
      </select>
    </div>
  );
}
