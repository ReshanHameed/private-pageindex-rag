import { useEffect, useRef, useState, useMemo, useImperativeHandle, forwardRef } from 'react';
import * as d3 from 'd3-force';
import type { TreeJSON, TreeNode } from '@/lib/types';
import GraphNode from './GraphNode';
import GraphEdge from './GraphEdge';

interface KnowledgeGraphProps {
  tree: TreeJSON;
  onNodeClick?: (node: TreeNode) => void;
  selectedNodeId?: string;
  isInspectTree?: boolean;
  activatedNodeIds?: string[];
  fetchedNodeIds?: string[];
  isStreaming?: boolean;
}

export interface KnowledgeGraphHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
}

interface ForceNode extends d3.SimulationNodeDatum {
  id: string;
  data: TreeNode;
  radius: number;
}

interface ForceLink extends d3.SimulationLinkDatum<ForceNode> {
  source: ForceNode;
  target: ForceNode;
}

const KnowledgeGraph = forwardRef<KnowledgeGraphHandle, KnowledgeGraphProps>(
  function KnowledgeGraph({
    tree,
    onNodeClick,
    selectedNodeId,
    isInspectTree = false,
    activatedNodeIds = [],
    fetchedNodeIds = [],
    isStreaming = false,
  }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [nodes, setNodes] = useState<ForceNode[]>([]);
    const [links, setLinks] = useState<ForceLink[]>([]);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const { width, height } = dimensions;

    // Camera and Interaction State
    const [camera, setCamera] = useState({ x: 0, y: 0, k: 1 });
    const [isAutoFit, setIsAutoFit] = useState(true);
    const isDragging = useRef(false);
    const lastPointer = useRef({ x: 0, y: 0 });

    // Track initial dimensions so physics can pack into the correct aspect ratio
    const initialSizeRef = useRef({ w: 800, h: 600 });
    if (width > 0 && initialSizeRef.current.w === 800) {
      initialSizeRef.current = { w: width, h: height };
    }

    useEffect(() => {
      if (!containerRef.current) return;
      const container = containerRef.current;
      const resizeObserver = new ResizeObserver((entries) => {
        if (!entries || entries.length === 0) return;
        const rect = entries[0].contentRect;
        if (rect.width > 0 && rect.height > 0) {
          setDimensions({ width: rect.width, height: rect.height });
        }
      });
      resizeObserver.observe(container);
      return () => {
        resizeObserver.unobserve(container);
        resizeObserver.disconnect();
      };
    }, []);

    // 1. Flatten tree to graph structure
    const graphData = useMemo(() => {
      const flatNodes: ForceNode[] = [];
      const flatLinks: ForceLink[] = [];

      const traverse = (node: TreeNode, parent?: ForceNode) => {
        const forceNode: ForceNode = {
          id: node.node_id,
          data: node,
          radius: node.nodes && node.nodes.length > 0 ? 16 : 10,
        };
        flatNodes.push(forceNode);

        if (parent) {
          flatLinks.push({
            source: parent,
            target: forceNode,
          });
        }

        node.nodes.forEach(child => traverse(child, forceNode));
      };

      if (tree.nodes) {
        tree.nodes.forEach(root => traverse(root));
      }

      return { nodes: flatNodes, links: flatLinks };
    }, [tree]);

    // 2. Setup D3 Force Simulation (Organic layout)
    useEffect(() => {
      const VIRTUAL_WIDTH = initialSizeRef.current.w;
      const VIRTUAL_HEIGHT = initialSizeRef.current.h;

      // Calculate the panel's aspect ratio. We will use this to squash the graph 
      // into a matching rectangle, perfectly filling the empty spaces.
      const aspectRatio = Math.max(0.5, Math.min(2.5, VIRTUAL_WIDTH / VIRTUAL_HEIGHT));
      const forceXStrength = 0.08 / Math.max(1, aspectRatio);
      const forceYStrength = 0.08 * Math.max(1, aspectRatio);

      // Deterministic initialization using a golden ratio spiral
      // This ensures the physics engine always resolves the tree into the EXACT SAME shape every time.
      graphData.nodes.forEach((node, idx) => {
        const angle = idx * 1.61803398875 * 2 * Math.PI; // Golden angle
        const radius = 10 + Math.sqrt(idx) * 20; // Increased spiral spread for larger nodes
        node.x = VIRTUAL_WIDTH / 2 + Math.cos(angle) * radius;
        node.y = VIRTUAL_HEIGHT / 2 + Math.sin(angle) * radius;
        node.vx = 0;
        node.vy = 0;
      });

      const simulation = d3.forceSimulation<ForceNode>(graphData.nodes)
        // Extremely weak background repulsion so nodes don't fly apart, but don't waste space
        .force('charge', d3.forceManyBody().strength(-25).distanceMax(200))
        // Tight rubber-band links. Short distance pulls nodes together tightly against the collision barrier!
        .force('link', d3.forceLink<ForceNode, ForceLink>(graphData.links).distance(25).strength(0.8))
        // Center gravity
        .force('center', d3.forceCenter(VIRTUAL_WIDTH / 2, VIRTUAL_HEIGHT / 2).strength(0.1))
        // Dynamic aspect ratio gravity to mathematically fill empty side/top spaces
        .force('x', d3.forceX(VIRTUAL_WIDTH / 2).strength(forceXStrength))
        .force('y', d3.forceY(VIRTUAL_HEIGHT / 2).strength(forceYStrength))
        // Softer collision barrier prevents violent bouncing during initialization but strictly resolves overlap eventually
        .force('collide', d3.forceCollide<ForceNode>().radius(d => d.radius + Math.min(75, d.data.title.length * 4) + 16).strength(0.7))
        .alpha(1)
        .alphaDecay(0.018) // Slower cooling allows for a smooth, cinematic unfolding
        .velocityDecay(0.75); // Extreme friction (molasses effect) completely eliminates jitter and bouncing

      // Continuous ticking to give the graph an "alive" feeling
      simulation.on('tick', () => {
        setNodes([...graphData.nodes]);
        setLinks([...graphData.links]);
      });

      // When a new graph loads, reset to auto-fit
      setIsAutoFit(true);

      return () => {
        simulation.stop();
      };
    }, [graphData]); 

    // Calculate auto-fit scale and translation to dynamically center and scale nodes inside panel dimensions
    const fitTransform = useMemo(() => {
      let tx = 0;
      let ty = 0;
      let k = 1;

      if (nodes.length > 0 && width > 0 && height > 0) {
        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;

        nodes.forEach((node) => {
          if (node.x !== undefined && node.y !== undefined) {
            const r = node.radius + 36; // Node radius plus label offset padding
            minX = Math.min(minX, node.x - r);
            maxX = Math.max(maxX, node.x + r);
            minY = Math.min(minY, node.y - r);
            maxY = Math.max(maxY, node.y + r);
          }
        });

        const graphW = maxX - minX;
        const graphH = maxY - minY;

        if (graphW > 0 && graphH > 0) {
          const centerX = (minX + maxX) / 2;
          const centerY = (minY + maxY) / 2;

          const padding = 32; // Screen-edge safety margin
          const availableW = Math.max(40, width - padding * 2);
          const availableH = Math.max(40, height - padding * 2);

          const scaleX = availableW / graphW;
          const scaleY = availableH / graphH;
          k = Math.min(scaleX, scaleY);
          
          // Limit zoom-in (max 1.4) so small graphs don't become cartoonishly huge.
          // Allow it to auto-fit large graphs entirely inside the panel without bleeding.
          k = Math.min(1.4, k);

          tx = width / 2 - centerX * k;
          ty = height / 2 - centerY * k;
        }
      }

      return { x: tx, y: ty, k };
    }, [nodes, width, height]);

    // The active transform is either the dynamic auto-fit, or the user's manual camera
    const activeTransform = isAutoFit ? fitTransform : camera;

    // Expose zoom/pan controls to parent via ref
    useImperativeHandle(ref, () => ({
      zoomIn() {
        setIsAutoFit(false);
        setCamera(prev => {
          const current = isAutoFit ? fitTransform : prev;
          const newK = Math.min(5, current.k * 1.3);
          const ratio = newK / current.k;
          const cx = width / 2;
          const cy = height / 2;
          return {
            x: cx - (cx - current.x) * ratio,
            y: cy - (cy - current.y) * ratio,
            k: newK
          };
        });
      },
      zoomOut() {
        setIsAutoFit(false);
        setCamera(prev => {
          const current = isAutoFit ? fitTransform : prev;
          const newK = Math.max(0.1, current.k / 1.3);
          const ratio = newK / current.k;
          const cx = width / 2;
          const cy = height / 2;
          return {
            x: cx - (cx - current.x) * ratio,
            y: cy - (cy - current.y) * ratio,
            k: newK
          };
        });
      },
      resetView() {
        setIsAutoFit(true);
      },
    }));

    // 3. Scroll-wheel zoom + pointer drag pan
    const handleWheel = (e: React.WheelEvent) => {
      e.preventDefault(); // Prevent page scroll if applicable
      setIsAutoFit(false);

      const rect = containerRef.current?.getBoundingClientRect();
      const pointerX = rect ? e.clientX - rect.left : width / 2;
      const pointerY = rect ? e.clientY - rect.top : height / 2;

      const scaleFactor = e.deltaY < 0 ? 1.1 : 0.9;
      
      setCamera(prev => {
        const current = isAutoFit ? fitTransform : prev;
        const newK = Math.max(0.1, Math.min(6, current.k * scaleFactor));
        const ratio = newK / current.k;

        return {
          x: pointerX - (pointerX - current.x) * ratio,
          y: pointerY - (pointerY - current.y) * ratio,
          k: newK
        };
      });
    };

    const handlePointerDown = (e: React.PointerEvent) => {
      isDragging.current = true;
      lastPointer.current = { x: e.clientX, y: e.clientY };
      e.currentTarget.setPointerCapture(e.pointerId);
      
      if (isAutoFit) {
        setIsAutoFit(false);
        setCamera({ x: fitTransform.x, y: fitTransform.y, k: fitTransform.k });
      }
    };

    const handlePointerMove = (e: React.PointerEvent) => {
      if (!isDragging.current) return;
      const dx = e.clientX - lastPointer.current.x;
      const dy = e.clientY - lastPointer.current.y;
      
      setCamera(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }));
      lastPointer.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerUp = (e: React.PointerEvent) => {
      isDragging.current = false;
      e.currentTarget.releasePointerCapture(e.pointerId);
    };

    return (
      <div 
        ref={containerRef} 
        className="w-full h-full overflow-hidden bg-bg-void/20 cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <svg width="100%" height="100%">
          <g transform={`translate(${activeTransform.x}, ${activeTransform.y}) scale(${activeTransform.k})`}>
            {/* Edges */}
            {links.map((link, i) => {
              const isTargetActivated = activatedNodeIds.includes(link.target.id);
              const isTargetFetched = fetchedNodeIds.includes(link.target.id);
              const isTargetSelected = link.target.id === selectedNodeId;

              return (
                <GraphEdge 
                  key={`link-${i}`} 
                  source={link.source} 
                  target={link.target} 
                  isActivated={isTargetActivated}
                  isFetched={isTargetFetched}
                  isSelected={isTargetSelected}
                />
              );
            })}
            {/* Nodes */}
            {nodes.map(node => (
              <GraphNode 
                key={node.id} 
                node={node} 
                isSelected={node.id === selectedNodeId}
                isInspectTree={isInspectTree}
                isActivated={activatedNodeIds.includes(node.id)}
                isFetched={fetchedNodeIds.includes(node.id)}
                isStreaming={isStreaming}
                onClick={() => onNodeClick?.(node.data)} 
              />
            ))}
          </g>
        </svg>
      </div>
    );
  }
);

export default KnowledgeGraph;
