import { useEffect, useState, useRef } from 'react';
import { animate, stagger } from 'animejs';

interface LoadingScreenProps {
  onComplete?: () => void;
}

export default function LoadingScreen({ onComplete }: LoadingScreenProps) {
  const [dots, setDots] = useState('·');
  const [visible, setVisible] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Fallback dots loader loop
    const dotsInterval = setInterval(() => {
      setDots((prev) => {
        if (prev === '·') return '· ·';
        if (prev === '· ·') return '· · ·';
        if (prev === '· · ·') return '· ·';
        return '·';
      });
    }, 400);

    if (isReducedMotion) {
      // Reduced motion: show content immediately, then dismiss quickly
      if (textRef.current) {
        Array.from(textRef.current.children).forEach((child) => {
          (child as HTMLElement).style.opacity = '1';
        });
      }
      const quickTimeout = setTimeout(() => {
        setVisible(false);
        if (onComplete) onComplete();
      }, 800);
      return () => {
        clearInterval(dotsInterval);
        clearTimeout(quickTimeout);
      };
    }

    // Staggered layout entrance animation
    if (textRef.current) {
      animate(textRef.current.children, {
        opacity: [0, 1],
        translateY: [20, 0],
        delay: stagger(150),
        duration: 1000,
        ease: 'outExpo'
      });
    }

    // Trigger complete fade-out after 2200ms
    const fadeTimeout = setTimeout(() => {
      if (containerRef.current) {
        animate(containerRef.current, {
          opacity: [1, 0],
          translateY: [0, -30],
          duration: 600,
          ease: 'outExpo',
          onComplete: () => {
            setVisible(false);
            if (onComplete) onComplete();
          }
        });
      }
    }, 2200);

    return () => {
      clearInterval(dotsInterval);
      clearTimeout(fadeTimeout);
    };
  }, [onComplete]);

  if (!visible) return null;

  return (
    <div
      id="loading-screen"
      ref={containerRef}
      className="fixed inset-0 z-[1000] flex flex-col items-center justify-center bg-bg-void text-text-primary select-none px-4"
    >
      <div
        ref={textRef}
        className="flex flex-col items-center max-w-[800px] w-full text-center"
      >
        {/* Decorative ASCII Terminal border */}
        <pre className="text-accent/40 font-mono text-[9px] sm:text-[11px] leading-none mb-6 font-bold select-none pointer-events-none">
{`┌────────────────────────────────────────────────────────────────────────┐
│           [BOOT_STAGE]: HYDRATING_REACT_APPLICATION_SHELL                │
└────────────────────────────────────────────────────────────────────────┘`}
        </pre>

        {/* Premium ASCII art title */}
        <pre className="text-accent font-mono text-[5px] sm:text-[7px] md:text-[10px] leading-none mb-8 font-bold select-none pointer-events-none">
{` ██████╗  █████╗  ██████╗ ███████╗   ██╗███╗   ██╗██████╗ ███████╗██╗  ██╗   ██████╗  █████╗  ██████╗ 
 ██╔══██╗██╔══██╗██╔════╝ ██╔════╝   ██║████╗  ██║██╔══██╗██╔════╝╚██╗██╔╝   ██╔══██╗██╔══██╗██╔════╝ 
 ██████╔╝███████║██║  ███╗█████╗     ██║██╔██╗ ██║██║  ██║█████╗   ╚███╔╝    ██████╔╝███████║██║  ███╗
 ██╔═══╝ ██╔══██║██║   ██║██╔══╝     ██║██║╚██╗██║██║  ██║██╔══╝   ██╔██╗    ██╔══██╗██╔══██║██║   ██║
 ██║     ██║  ██║╚██████╔╝███████╗   ██║██║ ╚████║██████╔╝███████╗██╔╝ ██╗   ██║  ██║██║  ██║╚██████╔╝
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ `}
        </pre>

        {/* Display details */}
        <h1 className="font-display text-text-primary text-xl sm:text-2xl font-medium tracking-tight mb-2">
          PRIVATE PAGEINDEX RAG
        </h1>
        <p className="font-sans text-text-secondary text-sm mb-8">
          Local-first document indexing and intelligence console
        </p>

        {/* Progress & Staggered character loader fallback */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-3 bg-bg-surface border border-border-dim px-6 py-2">
            <span className="font-mono text-xs text-text-tertiary select-none">
              [SYSTEM_LOAD]:
            </span>
            <span className="font-mono text-xs text-accent font-medium min-w-[70px] text-left">
              Loading {dots}
            </span>
          </div>
          
        </div>
      </div>
    </div>
  );
}
