import { useEffect, useState } from 'react';

interface ElapsedTimerProps {
  startedAt: string | null;
  finishedAt: string | null;
}

export default function ElapsedTimer({ startedAt, finishedAt }: ElapsedTimerProps) {
  const [seconds, setSeconds] = useState(() => {
    if (!startedAt) return 0;
    const start = new Date(startedAt).getTime();
    const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
    return Math.max(0, Math.floor((end - start) / 1000));
  });

  useEffect(() => {
    if (!startedAt) return;

    const start = new Date(startedAt).getTime();

    const calculateElapsed = () => {
      const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
      const elapsed = Math.max(0, Math.floor((end - start) / 1000));
      setSeconds(elapsed);
    };

    calculateElapsed();

    if (finishedAt) {
      return;
    }

    const interval = setInterval(calculateElapsed, 1000);
    return () => clearInterval(interval);
  }, [startedAt, finishedAt]);

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const timeString = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  return (
    <span className="font-mono text-[10px] tabular-nums select-none text-text-secondary tracking-tight">
      {timeString}
    </span>
  );
}
