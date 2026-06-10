import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback to render instead of the default ASCII error card */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * ASCII-styled error boundary.
 *
 * Catches React render errors and shows a terminal-themed error card
 * with a retry button and navigation back to the dashboard.
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex items-center justify-center min-h-[400px] p-8 animate-fade-in">
          <div className="border border-error/40 bg-bg-surface max-w-lg w-full flex flex-col">
            {/* Header */}
            <div className="px-4 py-3 border-b border-error/30 bg-bg-void/60 flex items-center gap-2 select-none">
              <AlertTriangle className="w-4 h-4 text-error" />
              <span className="font-mono text-xs font-bold text-error tracking-wide">
                ▒░▓ RENDER_ERROR ▓░▒
              </span>
            </div>

            {/* Body */}
            <div className="px-4 py-5 flex flex-col gap-4">
              <p className="font-sans text-sm text-text-secondary leading-relaxed">
                Something went wrong while rendering this section. The error has been logged to the browser console.
              </p>

              {this.state.error && (
                <div className="bg-bg-void border border-border-dim px-3 py-2 overflow-x-auto">
                  <pre className="font-mono text-[11px] text-error/80 whitespace-pre-wrap break-words">
                    {this.state.error.message}
                  </pre>
                </div>
              )}

              {this.state.errorInfo?.componentStack && (
                <details className="group">
                  <summary className="font-mono text-[10px] text-text-tertiary cursor-pointer hover:text-text-secondary select-none">
                    COMPONENT_STACK ▸
                  </summary>
                  <div className="mt-2 bg-bg-void border border-border-dim px-3 py-2 max-h-48 overflow-y-auto">
                    <pre className="font-mono text-[10px] text-text-tertiary whitespace-pre-wrap break-words">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                </details>
              )}
            </div>

            {/* Actions */}
            <div className="px-4 py-3 border-t border-border-dim flex items-center gap-3">
              <button
                onClick={this.handleRetry}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-accent bg-accent/10 text-accent text-xs font-mono font-bold hover:bg-accent/20 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" /> RETRY
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-border-default bg-bg-interactive text-text-secondary text-xs font-mono hover:text-text-primary hover:border-border-bright transition-colors cursor-pointer"
              >
                <Home className="w-3 h-3" /> DASHBOARD
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
