import { useNavigate } from 'react-router-dom';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { FileText, Upload, Home } from 'lucide-react';
import { useAppStore } from '@/lib/store';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const documents = useAppStore((s) => s.documents);

  const completedDocs = documents.filter((d) => d.status === 'completed');

  const handleSelect = (callback: () => void) => {
    onOpenChange(false);
    callback();
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <Command className="bg-bg-surface border-border-default">
        <CommandInput
          placeholder="Type a command or search documents..."
          className="font-mono text-sm border border-border-default"
        />
        <CommandList className="max-h-[400px]">
          <CommandEmpty className="font-mono text-xs text-text-tertiary py-6 text-center">
            NO_RESULTS_FOUND
          </CommandEmpty>

          <CommandGroup heading="Navigation" className="font-mono text-[10px] text-text-tertiary uppercase">
            <CommandItem
              onSelect={() => handleSelect(() => navigate('/'))}
              className="font-sans text-sm cursor-pointer transition-colors duration-200"
            >
              <Home className="size-4 mr-2 text-text-secondary" />
              Dashboard
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Actions" className="font-mono text-[10px] text-text-tertiary uppercase">
            <CommandItem
              onSelect={() => handleSelect(() => {
                navigate('/');
                // Trigger upload zone focus after navigation
                setTimeout(() => {
                  document.querySelector<HTMLElement>('[data-upload-zone]')?.click();
                }, 100);
              })}
              className="font-sans text-sm cursor-pointer transition-colors duration-200"
            >
              <Upload className="size-4 mr-2 text-text-secondary" />
              Upload Document
            </CommandItem>
          </CommandGroup>

          {completedDocs.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Documents" className="font-mono text-[10px] text-text-tertiary uppercase">
                {completedDocs.map((doc) => (
                  <CommandItem
                    key={doc.id}
                    onSelect={() => handleSelect(() => navigate(`/documents/${doc.id}`))}
                    className="font-sans text-sm cursor-pointer transition-colors duration-200"
                  >
                    <FileText className="size-4 mr-2 text-text-secondary" />
                    <span className="flex-1 truncate">{doc.filename}</span>
                    <span className="font-mono text-[10px] text-text-tertiary ml-2">
                      {doc.page_count} pages
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
