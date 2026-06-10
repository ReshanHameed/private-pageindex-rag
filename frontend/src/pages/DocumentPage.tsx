import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Network } from 'lucide-react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import KnowledgeGraph, { type KnowledgeGraphHandle } from '@/components/graph/KnowledgeGraph';
import GraphControls from '@/components/graph/GraphControls';
import NodeDetails from '@/components/graph/NodeDetails';
import ChatPanel from '@/components/chat/ChatPanel';
import { api } from '@/lib/api';
import type { TreeJSON, TreeNode, DocumentRecord } from '@/lib/types';
import { toast } from 'sonner';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useStreamStore } from '@/lib/traceStore';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useIsMobile } from '@/hooks/use-mobile';
import { useAppStore } from '@/lib/store';

export default function DocumentPage() {
  const { docId } = useParams();
  const graphRef = useRef<KnowledgeGraphHandle>(null);
  const isMobile = useIsMobile();

  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [tree, setTree] = useState<TreeJSON | null>(null);
  const chats = useAppStore((s) => s.currentChats);
  const setChats = useAppStore((s) => s.setCurrentChats);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [graphKey, setGraphKey] = useState(0);

  // Subscribe to live tracing / SSE retrieval states
  const isStreaming = useStreamStore((s) => s.isStreaming);
  const activatedNodeIds = useStreamStore((s) => s.activatedNodeIds);
  const fetchedNodeIds = useStreamStore((s) => s.fetchedNodeIds);
  const currentStep = useStreamStore((s) => s.currentStep);

  // Clean up store on unmount
  useEffect(() => {
    return () => {
      useStreamStore.getState().reset();
    };
  }, []);

  // Keyboard shortcut: Escape to deselect current node
  useKeyboardShortcuts({
    onEscape: () => setSelectedNode(null),
  });

  useEffect(() => {
    if (!docId) return;

    // Reset retrieval stream state and selections when switching documents
    useStreamStore.getState().reset();

    Promise.all([
      api.fetchDocument(docId),
      api.fetchDocumentTree(docId)
    ]).then(([d, t]) => {
      setSelectedNode(null);
      setDoc(d);
      setTree(t);
    }).catch(err => {
      console.error(err);
      toast.error('Failed to load document data');
    });
  }, [docId, setChats]);

  // Recursively find a node by checked page number bounds
  const findNodeByPage = (nodes: TreeNode[], pageNum: number): TreeNode | null => {
    for (const node of nodes) {
      if (pageNum >= node.start_page && pageNum <= node.end_page) {
        return node;
      }
      if (node.nodes && node.nodes.length > 0) {
        const found = findNodeByPage(node.nodes, pageNum);
        if (found) return found;
      }
    }
    return null;
  };

  const handleCitationClick = (pageNum: number) => {
    if (!tree) return;
    const node = findNodeByPage(tree.nodes, pageNum);
    if (node) {
      setSelectedNode(node);
      toast.success(`Highlighted node "${node.title}" (pages ${node.start_page}-${node.end_page})`);
    } else {
      toast.error(`No graph node found containing page ${pageNum}`);
    }
  };

  const handleAsk = async (question: string) => {
    if (!docId) return;
    setIsChatLoading(true);

    const store = useStreamStore.getState();
    store.startStream(question);

    const controller = new AbortController();

    try {
      await fetchEventSource(`/api/documents/${docId}/ask/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          model: localStorage.getItem('selected_model') || '',
          session_id: useAppStore.getState().activeSessionId || undefined,
        }),
        signal: controller.signal,
        async onopen(response) {
          if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
            return; // connection successful
          }
          throw new Error('Failed to open event stream connection');
        },
        onmessage(msg) {
          try {
            const data = JSON.parse(msg.data);
            if (data.type === 'trace') {
              store.addTraceEvent(data);
            } else if (data.type === 'token') {
              store.appendToken(data.text);
            } else if (data.type === 'done') {
              store.completeStream(data.chat_id, data.answer, data.citations);
              // Fetch completed chats history to persist
              const appStore = useAppStore.getState();
              appStore.fetchSessionsAndChats(docId, data.session_id);
            } else if (data.type === 'error') {
              store.setError(data.detail);
              toast.error(data.detail);
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        },
        onerror(err) {
          console.error('SSE Error:', err);
          store.setError(err instanceof Error ? err.message : String(err));
          controller.abort(); // prevent automatic reconnection retries
          throw err;
        }
      });
    } catch (err) {
      console.error('SSE Ask connection failed:', err);
      toast.error('Failed to get streaming answer');
    } finally {
      setIsChatLoading(false);
    }
  };

  if (!doc) {
    return <div className="flex items-center justify-center h-[calc(100vh-220px)] animate-pulse font-mono text-sm">LOADING_DOCUMENT...</div>;
  }

  return (
    <div className="flex flex-col gap-4 w-full h-full animate-fade-in overflow-hidden">
      
      {/* Document header with back button */}
      <div className="flex items-center justify-between border-b border-border-dim pb-4 select-none shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-1 border border-border-dim bg-bg-surface hover:bg-bg-interactive text-text-secondary hover:text-text-primary cursor-pointer transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex flex-col">
            <h2 className="text-lg font-display font-medium text-text-primary leading-tight">
              {doc.filename}
            </h2>
            <span className="font-mono text-[13px] text-text-tertiary uppercase">
              {isMobile ? `${doc.page_count} PAGES` : `DOCUMENT_ID: ${doc.id} · ${doc.page_count} PAGES · ${doc.status}`}
            </span>
          </div>
        </div>
      </div>

      {/* Main split workarea — resizable panels on desktop, vertical stack on mobile */}
      {isMobile ? (
        /* Mobile: vertical stack */
        <div className="flex flex-col gap-4">
          {/* Graph section (fixed height on mobile) */}
          <div className="h-[300px] border border-border-default bg-bg-surface/60 flex flex-col relative overflow-hidden">
            <div className="p-3 border-b border-border-dim bg-bg-void/60 flex items-center justify-between select-none z-10">
              <span className="font-mono text-xs font-bold text-text-secondary flex items-center gap-2">
                <Network className="w-4 h-4 text-accent" /> KNOWLEDGE_GRAPH
              </span>
            </div>
            <div className="flex-1 relative">
              {tree ? (
                <KnowledgeGraph 
                  ref={graphRef}
                  key={graphKey}
                  tree={tree} 
                  onNodeClick={setSelectedNode}
                  selectedNodeId={selectedNode?.node_id}
                  isInspectTree={currentStep === 'inspect_tree'}
                  activatedNodeIds={activatedNodeIds}
                  fetchedNodeIds={fetchedNodeIds}
                  isStreaming={isStreaming}
                />
              ) : (
                <div className="flex items-center justify-center h-full font-mono text-xs text-text-tertiary">
                  {doc.status === 'completed' ? 'NO_TREE_FOUND' : 'DOCUMENT_PROCESSING...'}
                </div>
              )}
              <GraphControls 
                onZoomIn={() => graphRef.current?.zoomIn()}
                onZoomOut={() => graphRef.current?.zoomOut()}
                onReset={() => {
                  setGraphKey(k => k + 1);
                  setSelectedNode(null);
                }}
              />
              <NodeDetails node={selectedNode} onClose={() => setSelectedNode(null)} />
            </div>
          </div>

          {/* Chat section (fills remaining space on mobile) */}
          <div className="h-[calc(100vh-520px)] min-h-[300px] border border-border-default bg-bg-surface flex flex-col overflow-hidden">
            <ChatPanel 
              chats={chats} 
              onAsk={handleAsk} 
              isLoading={isChatLoading} 
              docId={docId ?? ''}
              onCitationClick={handleCitationClick}
            />
          </div>
        </div>
      ) : (
        /* Desktop: resizable horizontal panels */
        <div className="flex-1 min-h-0">
          <PanelGroup orientation="horizontal" className="h-full">

            {/* Left panel: Knowledge Graph */}
            <Panel defaultSize={60} minSize={30} className="h-full">
              <div className="border border-border-default bg-bg-surface/60 flex flex-col relative h-full overflow-hidden">
                {/* Header bar */}
                <div className="p-3 border-b border-border-dim bg-bg-void/60 flex items-center justify-between select-none z-10">
                  <span className="font-mono text-xs font-bold text-text-secondary flex items-center gap-2">
                    <Network className="w-4 h-4 text-accent" /> SPATIAL_KNOWLEDGE_GRAPH
                  </span>
                </div>

                <div className="flex-1 relative">
                  {tree ? (
                    <KnowledgeGraph 
                      ref={graphRef}
                      key={graphKey}
                      tree={tree} 
                      onNodeClick={setSelectedNode}
                      selectedNodeId={selectedNode?.node_id}
                      isInspectTree={currentStep === 'inspect_tree'}
                      activatedNodeIds={activatedNodeIds}
                      fetchedNodeIds={fetchedNodeIds}
                      isStreaming={isStreaming}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full font-mono text-xs text-text-tertiary">
                      {doc.status === 'completed' ? 'NO_TREE_FOUND' : 'DOCUMENT_PROCESSING...'}
                    </div>
                  )}
                  
                  <GraphControls 
                    onZoomIn={() => graphRef.current?.zoomIn()}
                    onZoomOut={() => graphRef.current?.zoomOut()}
                    onReset={() => {
                      setGraphKey(k => k + 1);
                      setSelectedNode(null);
                    }}
                  />
                  <NodeDetails node={selectedNode} onClose={() => setSelectedNode(null)} />
                </div>
              </div>
            </Panel>

            {/* Resize handle */}
            <PanelResizeHandle className="w-6 flex items-center justify-center group cursor-col-resize">
              <div className="w-px h-full bg-border-dim group-hover:bg-accent/40 transition-colors" />
            </PanelResizeHandle>

            {/* Right panel: Chat Console */}
            <Panel defaultSize={40} minSize={25} className="h-full">
              <div className="border border-border-default bg-bg-surface flex flex-col h-full overflow-hidden">
                <ChatPanel 
                  chats={chats} 
                  onAsk={handleAsk} 
                  isLoading={isChatLoading} 
                  docId={docId ?? ''}
                  onCitationClick={handleCitationClick}
                />
              </div>
            </Panel>

          </PanelGroup>
        </div>
      )}
    </div>
  );
}
