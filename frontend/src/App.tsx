import { useState, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import LoadingScreen from './components/LoadingScreen';
import InteractiveBackground from './components/InteractiveBackground';
import AppShell from './components/layout/AppShell';
import ErrorBoundary from './components/ErrorBoundary';
import { Toaster } from './components/ui/sonner';
import { TooltipProvider } from './components/ui/tooltip';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const DocumentPage = lazy(() => import('./pages/DocumentPage'));
const TracePage = lazy(() => import('./pages/TracePage'));

export default function App() {
  const [loading, setLoading] = useState(true);

  return (
    <>
      {/* Feature 1: ASCII Loading Screen (Overlay) */}
      <LoadingScreen onComplete={() => setLoading(false)} />
      
      {/* Feature 2: Interactive Background Matrix (Canvas) */}
      <InteractiveBackground />

      {/* Global Toast Notifications */}
      <Toaster />


      {/* App Router Workspace */}
      {!loading && (
        <TooltipProvider>
          <BrowserRouter>
            <AppShell>
              <ErrorBoundary>
                <Suspense
                  fallback={
                    <div className="flex items-center justify-center h-full min-h-[500px]">
                      <Loader2 className="size-6 animate-spin text-accent" />
                    </div>
                  }
                >
                  <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/documents/:docId" element={<DocumentPage />} />
                    <Route path="/documents/:docId/chats/:chatId/trace" element={<TracePage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </ErrorBoundary>
            </AppShell>
          </BrowserRouter>
        </TooltipProvider>
      )}
    </>
  );
}

