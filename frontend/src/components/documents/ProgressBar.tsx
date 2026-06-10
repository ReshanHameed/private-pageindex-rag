import { useEffect, useRef, useState } from 'react';
import { animate } from 'animejs';

interface ProgressBarProps {
  value: number; // 0-100
}

export default function ProgressBar({ value }: ProgressBarProps) {
  const [animatedValue, setAnimatedValue] = useState(value);
  const prevValue = useRef(value);

  // Sync state with prop during render if reduced motion is enabled to avoid effect warning
  const prefersReduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  if (prefersReduced && animatedValue !== value) {
    setAnimatedValue(value);
  }

  useEffect(() => {
    if (prefersReduced) return;

    const obj = { val: prevValue.current };
    const anim = animate(obj, {
      val: value,
      round: 1,
      duration: 500,
      ease: 'outQuad',
      onUpdate: () => {
        setAnimatedValue(obj.val);
      },
    });

    prevValue.current = value;
    return () => {
      anim.cancel();
    };
  }, [value, prefersReduced]);

  const totalBlocks = 30;
  const filledBlocks = Math.min(totalBlocks, Math.max(0, Math.round((animatedValue / 100) * totalBlocks)));
  const emptyBlocks = Math.max(0, totalBlocks - filledBlocks);

  const blockString = `[${'█'.repeat(filledBlocks)}${'-'.repeat(emptyBlocks)}]`;

  return (
    <div className="flex items-center gap-2 font-mono whitespace-nowrap flex-nowrap">
      <span
        className="text-accent text-xs leading-none select-none tracking-tighter transition-all duration-200 whitespace-nowrap"
        style={{ textShadow: filledBlocks > 0 ? '0 0 6px rgba(45, 212, 168, 0.4)' : 'none' }}
      >
        {blockString}
      </span>
      <span className="text-[10px] text-text-primary font-bold w-6 text-right tabular-nums">
        {Math.round(animatedValue)}%
      </span>
    </div>
  );
}
