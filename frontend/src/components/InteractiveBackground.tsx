import { useEffect, useRef } from 'react';

const GLYPHS = ['.', '·', '+', '*', '#', '@', '%'];
const CELL_SIZE = 18; // Spacing in pixels between grid cells
const MOUSE_RADIUS = 100; // Attraction/brighten radius
const IDLE_TIMEOUT = 5000; // 5 seconds of inactivity triggers ripple

export default function InteractiveBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000, active: false });
  const lastMoveTimeRef = useRef(0);

  useEffect(() => {
    lastMoveTimeRef.current = Date.now();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Detect prefers-reduced-motion
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let isReducedMotion = reducedMotionQuery.matches;

    const handleReducedMotionChange = (e: MediaQueryListEvent) => {
      isReducedMotion = e.matches;
      resizeCanvas();
    };
    reducedMotionQuery.addEventListener('change', handleReducedMotionChange);

    // Track mouse position
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY, active: true };
      lastMoveTimeRef.current = Date.now();
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    // Track scroll position — mutate DOM style directly to avoid React re-renders
    const handleScroll = () => {
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (docHeight > 0 && wrapperRef.current) {
        const ratio = window.scrollY / docHeight;
        const r = 12 + Math.floor(ratio * 10);
        const g = 12 + Math.floor(ratio * 15);
        const b = 14 + Math.floor(ratio * 12);
        wrapperRef.current.style.background = `radial-gradient(circle at 50% 50%, rgba(12,12,14,1) 0%, rgba(${r},${g},${b},1) 100%)`;
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Grid details
    let cols = 0;
    let rows = 0;
    interface Cell {
      x: number;
      y: number;
      char: string;
      baseOpacity: number;
      currentOpacity: number;
    }
    let grid: Cell[] = [];

    const resizeCanvas = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;

      cols = Math.ceil(width / CELL_SIZE) + 1;
      rows = Math.ceil(height / CELL_SIZE) + 1;
      
      grid = [];
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          grid.push({
            x: c * CELL_SIZE,
            y: r * CELL_SIZE,
            char: GLYPHS[Math.floor(Math.random() * GLYPHS.length)],
            // Baseline opacity for each glyph (visible but subtle)
            baseOpacity: Math.random() * 0.4 + 0.15,
            currentOpacity: 0
          });
        }
      }

      if (isReducedMotion) {
        drawStaticGrid();
      }
    };

    const drawStaticGrid = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillStyle = 'rgba(45, 212, 168, 0.04)'; // faint but visible static grid
      grid.forEach(cell => {
        ctx.fillText(cell.char, cell.x, cell.y);
      });
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // 60 FPS Render Loop
    let animationFrameId: number;
    const fpsLimit = 60;
    let lastTime = performance.now();

    const render = (time: number) => {
      if (isReducedMotion) return;

      animationFrameId = requestAnimationFrame(render);

      // Cap at 60fps
      const elapsed = time - lastTime;
      const interval = 1000 / fpsLimit;
      if (elapsed < interval) return;
      lastTime = time - (elapsed % interval);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.font = '11px "JetBrains Mono", monospace';

      const isIdle = Date.now() - lastMoveTimeRef.current > IDLE_TIMEOUT;
      const rippleTime = time * 0.0015; // Speed multiplier for ripple waves

      grid.forEach(cell => {
        let hoverFactor = 0;
        
        // Mouse reactivity
        if (mouseRef.current.active) {
          const dx = cell.x - mouseRef.current.x;
          const dy = cell.y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < MOUSE_RADIUS) {
            // Gaussian-like falloff curve
            hoverFactor = Math.exp(-Math.pow(dist / (MOUSE_RADIUS * 0.7), 2)) * 1.8;
          }
        }

        // Idle state waves (perpetual wave ripple when inactive)
        let rippleFactor = 0;
        if (isIdle) {
          const gridCenterX = canvas.width / 2;
          const gridCenterY = canvas.height / 2;
          const dx = cell.x - gridCenterX;
          const dy = cell.y - gridCenterY;
          const distFromCenter = Math.sqrt(dx * dx + dy * dy);
          
          // Wave equation radiating outward from the center
          rippleFactor = (Math.sin(distFromCenter * 0.008 - rippleTime * 2) + 1) * 0.4;
        }

        // Calculate final opacity — visible at idle, brighter on hover
        const targetOpacity = cell.baseOpacity * (1 + hoverFactor * 3 + rippleFactor);
        
        // Smooth interpolation
        cell.currentOpacity += (targetOpacity - cell.currentOpacity) * 0.15;
        // Cap at 0.15 for idle, up to 0.35 on direct hover
        const opacity = Math.min(cell.currentOpacity * 0.2, hoverFactor > 0.1 ? 0.35 : 0.15);

        if (opacity > 0.005) {
          ctx.fillStyle = `rgba(45, 212, 168, ${opacity})`;
          ctx.fillText(cell.char, cell.x, cell.y);
        }
      });
    };

    if (!isReducedMotion) {
      animationFrameId = requestAnimationFrame(render);
    }

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('scroll', handleScroll);
      reducedMotionQuery.removeEventListener('change', handleReducedMotionChange);
    };
  }, []);

  return (
    <div
      ref={wrapperRef}
      style={{ contentVisibility: 'auto' as const }}
      className="fixed inset-0 -z-50 w-full h-full transition-all duration-700 ease-out select-none pointer-events-none bg-bg-void"
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
      />
    </div>
  );
}
