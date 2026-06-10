import { useEffect } from 'react';

interface UseKeyboardShortcutsOptions {
  onCommandPalette?: () => void;
  onEscape?: () => void;
}

/**
 * Global keyboard shortcuts:
 * - Ctrl+K / Cmd+K → open command palette
 * - Escape → dismiss (close modals, deselect nodes)
 */
export function useKeyboardShortcuts({
  onCommandPalette,
  onEscape,
}: UseKeyboardShortcutsOptions) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K or Cmd+K → command palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        onCommandPalette?.();
        return;
      }

      // Escape → dismiss
      if (e.key === 'Escape') {
        onEscape?.();
        return;
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onCommandPalette, onEscape]);
}
