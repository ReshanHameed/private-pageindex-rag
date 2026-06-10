import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layers, MessageSquare, FilePlus, Database, ChevronRight, Trash2 } from 'lucide-react';
import { useAppStore } from '../../lib/store';
import OllamaStatus from './OllamaStatus';
import ModelPicker from './ModelPicker';

import CommandPalette from '../CommandPalette';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarTrigger,
  SidebarInset,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarMenuAction,
} from "@/components/ui/sidebar"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { documents, initialize, cleanup, currentSessions, activeSessionId, fetchSessionsAndChats } = useAppStore();
  const location = useLocation();
  const docIdMatch = location.pathname.match(/^\/documents\/([^/]+)/);
  const docId = docIdMatch ? docIdMatch[1] : null;

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useEffect(() => {
    if (docId) {
      fetchSessionsAndChats(docId, activeSessionId);
    }
  }, [docId, fetchSessionsAndChats]);

  // Keyboard shortcut Ctrl+K to open/close Command Palette
  useKeyboardShortcuts({
    onCommandPalette: () => setCommandPaletteOpen((prev) => !prev),
    onEscape: () => {},
  });

  // Initialize store and fetch data on mount
  useEffect(() => {
    initialize();
    return () => cleanup();
  }, [initialize, cleanup]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-transparent text-text-primary font-sans relative">
      {/* Ctrl+K Search Command Palette */}
      <CommandPalette open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen} />

      {/* 1. Header (Always Full Width) */}
      <header className="flex-none sticky top-0 z-sticky h-14 bg-bg-surface border-b border-border-dim px-4 flex items-center justify-between select-none">
        {/* Left Section: Logo */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="flex items-center justify-center w-8 h-8 bg-bg-interactive border border-border-default">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-accent">
                <path d="M4 17L10 11L4 5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter"/>
                <line x1="12" y1="17" x2="20" y2="17" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square"/>
              </svg>
            </div>
            
            {/* Hide brand text on very small screens */}
            <div className="hidden sm:flex flex-col">
              <span className="font-display font-bold text-sm tracking-wide text-text-primary">
                PRIVATE PAGEINDEX
              </span>
              <span className="font-mono text-[9px] text-accent leading-none font-bold uppercase tracking-widest">
                LOCAL RAG ENGINE
              </span>
            </div>
          </Link>
        </div>

        {/* Center/Right Section: Status & Controls */}
        <div className="flex items-center gap-2 md:gap-4">
          <OllamaStatus />
          <ModelPicker />
        </div>
      </header>

      {/* 2. Middle Workspace (Sidebar + Main Content) */}
      <div className="flex-1 flex overflow-hidden min-h-0 relative">
        <SidebarProvider className="h-full w-full relative">
          
          <Sidebar collapsible="icon" className="border-r border-border-dim bg-bg-surface/95 z-sidebar">
            <SidebarContent className="font-mono text-xs overflow-y-auto px-2 py-4 gap-4">
              
              {/* Home/Upload Button */}
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton 
                    asChild 
                    tooltip="Add Document"
                    className={`transition-colors ${
                      location.pathname === '/' 
                        ? '!bg-bg-interactive !text-accent hover:!bg-bg-interactive hover:!text-accent' 
                        : 'hover:!bg-bg-interactive hover:!text-accent text-text-secondary'
                    }`}
                  >
                    <Link to="/">
                      <FilePlus className="w-4 h-4 text-accent" />
                      <span className="font-bold tracking-wider uppercase">Add Document</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>

              {/* Documents Collapsible Category */}
              <SidebarMenu className="mt-2">
                <Collapsible defaultOpen className="group/collapsible">
                  <SidebarMenuItem>
                    <CollapsibleTrigger asChild>
                      <SidebarMenuButton tooltip="Documents" className="text-text-secondary hover:!bg-bg-interactive hover:!text-accent transition-colors">
                        <Database className="w-4 h-4 text-accent" />
                        <span className="font-bold tracking-wider uppercase">Documents</span>
                        <ChevronRight className="ml-auto w-4 h-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90 text-text-tertiary" />
                      </SidebarMenuButton>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {documents.map((doc) => {
                          const isOptimistic = doc.id.startsWith('temp-');
                          const isActive = docId === doc.id;
                          
                          return (
                            <SidebarMenuSubItem key={doc.id}>
                              <SidebarMenuSubButton 
                                asChild 
                                className={`h-auto min-h-8 py-1.5 transition-colors ${
                                  doc.status === 'processing' 
                                    ? 'border border-warning/80 bg-bg-void !text-warning animate-pulse'
                                    : isActive 
                                    ? '!bg-bg-interactive !text-accent hover:!bg-bg-interactive hover:!text-accent font-medium border border-transparent' 
                                    : 'text-text-secondary hover:!bg-bg-interactive hover:!text-accent border border-transparent'
                                } ${
                                  doc.status === 'failed' ? 'text-error' : ''
                                }`}
                              >
                                {doc.status === 'completed' && !isOptimistic ? (
                                  <Link to={`/documents/${doc.id}`} className="flex items-center gap-2 w-full">
                                    <div className="flex flex-col min-w-0 flex-1">
                                      <span className="truncate">{doc.filename}</span>
                                    </div>
                                  </Link>
                                ) : (
                                  <div className="flex items-center gap-2 w-full cursor-not-allowed">
                                    <div className="flex flex-col min-w-0 flex-1">
                                      <span className="truncate opacity-70">{doc.filename}</span>
                                      <span className="text-[9px] uppercase font-bold">
                                        {doc.status === 'processing' ? `${doc.progress_percent}%` : doc.status}
                                      </span>
                                    </div>
                                  </div>
                                )}
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          );
                        })}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>
              </SidebarMenu>

              {/* Chat Sessions Section */}
              {docId && currentSessions.length > 0 && (
                <>
                  <div className="h-px bg-border-dim mx-2 my-2 group-data-[collapsible=icon]:hidden" />
                  <SidebarMenu className="gap-1">
                    {currentSessions.map((session) => {
                      const isActive = activeSessionId === session.id;
                      return (
                        <SidebarMenuItem key={session.id}>
                          <SidebarMenuButton 
                            asChild
                            tooltip="Chat Session"
                            className={`h-auto min-h-8 py-1.5 transition-colors cursor-pointer ${
                              isActive 
                                ? '!bg-bg-interactive !text-accent hover:!bg-bg-interactive hover:!text-accent font-medium' 
                                : 'text-text-secondary hover:!bg-bg-interactive hover:!text-accent'
                            }`}
                          >
                            <Link to={`/documents/${docId}`} onClick={() => fetchSessionsAndChats(docId, session.id)} className="flex items-start gap-2 w-full">
                              <MessageSquare className="w-4 h-4 shrink-0 mt-0.5" />
                              <div className="flex flex-col min-w-0 flex-1 group-data-[collapsible=icon]:hidden pr-6">
                                <span className="truncate text-[11px] leading-tight">Session</span>
                                <span className="text-[8px] text-text-tertiary font-bold uppercase mt-1">
                                  {new Date(session.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </Link>
                          </SidebarMenuButton>
                          <SidebarMenuAction
                            showOnHover
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              if (window.confirm('Are you sure you want to delete this session?')) {
                                useAppStore.getState().deleteSession(docId, session.id);
                              }
                            }}
                            className="text-text-tertiary hover:text-error hover:bg-error/10 cursor-pointer"
                            aria-label="Delete session"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </SidebarMenuAction>
                        </SidebarMenuItem>
                      );
                    })}
                  </SidebarMenu>
                </>
              )}
            </SidebarContent>
          </Sidebar>

          {/* Main Content Area */}
          <SidebarInset className="flex-1 flex flex-col bg-transparent overflow-hidden relative">
            {/* Floating Toggle */}
            <div className="absolute top-4 left-4 z-20">
              <SidebarTrigger className="text-text-secondary hover:text-text-primary hover:bg-bg-interactive border border-transparent hover:border-border-default cursor-pointer transition-colors bg-bg-surface/80 backdrop-blur" />
            </div>

            <main className={`flex-1 overflow-hidden relative flex flex-col ${docId ? '' : 'items-center pt-10'}`}>
              <div className={`w-full flex-1 flex flex-col overflow-hidden relative ${
                docId ? 'max-w-none w-full pl-14 pr-6 pb-6 pt-4' : 'max-w-[1140px] px-4 md:px-8 pt-4 pb-0 md:pt-8 md:pb-4'
              }`}>
                {children}
              </div>
            </main>
          </SidebarInset>

        </SidebarProvider>
      </div>

      {/* 3. Footer (Always Full Width) */}
      <footer className="flex-none h-10 bg-bg-surface border-t border-border-dim px-4 flex items-center justify-between font-mono text-[10px] text-text-tertiary select-none z-10">
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline">PRIVATE_PAGEINDEX_RAG_V0.1.0</span>
          <span className="hidden sm:inline">//</span>
          <span className="text-accent">▒░▓ LOCAL_WORKSPACE_VERIFIED ▓░▒</span>
          <div className="ml-4 flex items-center gap-2 text-text-secondary">
            <span>Inference: <span className="text-accent font-semibold">Ollama</span></span>
            <span>RAG Boundary: <span className="text-success font-semibold">local_only</span></span>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <Layers className="w-3 h-3 text-text-tertiary" />
          </span>
          <span>//</span>
          <span>© 2026</span>
        </div>
      </footer>
    </div>
  );
}
