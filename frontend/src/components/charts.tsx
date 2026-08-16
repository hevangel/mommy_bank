/** Hand-rolled SVG charts — no chart library. */

export function Sparkline({
  data,
  width = 220,
  height = 56,
  stroke = "#F17FB6",
  fill = "rgba(241,127,182,.15)",
  className = "",
}: {
  data: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  className?: string;
}) {
  if (data.length < 2) {
    return (
      <div className="flex h-14 items-center text-xs text-ink/35" style={{ width }}>
        not enough history yet
      </div>
    );
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 4;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${width - pad},${height} L${pad},${height} Z`;
  const last = pts[pts.length - 1];
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={className} style={{ width, height }} aria-hidden>
      <path d={area} fill={fill} />
      <path d={line} fill="none" stroke={stroke} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="4" fill={stroke} stroke="#fff" strokeWidth="2" />
    </svg>
  );
}

/** Animated number that counts up when the value changes. */
import { useEffect, useRef, useState } from "react";

export function CountUp({
  value,
  format,
  className = "",
}: {
  value: number;
  format: (v: number) => string;
  className?: string;
}) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    if (from === value) return;
    const dur = 380;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      setDisplay(value);
      fromRef.current = value;
    };
    const start = performance.now();
    const tick = (now: number) => {
      if (done) return;
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (value - from) * eased));
      if (t >= 1) finish();
      else rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    // rAF is throttled/paused in occluded renderers — always land on the final value
    const safety = setTimeout(finish, dur + 120);
    return () => {
      cancelAnimationFrame(rafRef.current);
      clearTimeout(safety);
    };
  }, [value]);

  return <span className={`tabular ${className}`}>{format(display)}</span>;
}
