/** Decorative background scenes — soft waves, clouds and floating coins. */
export function WaveBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-piggysoft blur-3xl opacity-70" />
      <div className="absolute -right-32 top-40 h-[28rem] w-[28rem] rounded-full bg-skysoft blur-3xl opacity-70" />
      <div className="absolute -left-20 bottom-0 h-80 w-80 rounded-full bg-mintsoft blur-3xl opacity-60" />
      <svg
        className="absolute bottom-0 left-0 w-full"
        viewBox="0 0 1440 220"
        preserveAspectRatio="none"
        style={{ height: 180 }}
      >
        <path
          d="M0 96 C 240 20 480 180 720 110 C 960 40 1200 160 1440 80 L1440 220 L0 220 Z"
          fill="#FDE7F1"
          opacity="0.8"
        />
        <path
          d="M0 150 C 260 80 520 210 780 150 C 1040 90 1240 200 1440 140 L1440 220 L0 220 Z"
          fill="#E2F7EF"
          opacity="0.8"
        />
      </svg>
    </div>
  );
}

export function Cloud({
  className = "",
  opacity = 0.9,
  style,
}: {
  className?: string;
  opacity?: number;
  style?: React.CSSProperties;
}) {
  return (
    <svg viewBox="0 0 120 50" className={className} style={{ opacity, ...style }} aria-hidden>
      <path
        d="M20 40 a14 14 0 0 1 6-27 a18 18 0 0 1 34-6 a15 15 0 0 1 24 8 a12 12 0 0 1 6 25 z"
        fill="#fff"
      />
    </svg>
  );
}

export function FloatingCoins() {
  const coins = [
    { left: "8%", top: "18%", size: 26, delay: "0s", color: "#F5C445" },
    { left: "86%", top: "12%", size: 20, delay: "1.2s", color: "#FBC4DD" },
    { left: "76%", top: "62%", size: 16, delay: "0.6s", color: "#A5D8FF" },
    { left: "14%", top: "70%", size: 18, delay: "1.8s", color: "#C4B5FD" },
  ];
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {coins.map((c, i) => (
        <svg
          key={i}
          viewBox="0 0 40 40"
          width={c.size}
          height={c.size}
          className="animate-float absolute"
          style={{ left: c.left, top: c.top, animationDelay: c.delay }}
        >
          <circle cx="20" cy="20" r="17" fill={c.color} stroke="rgba(59,51,85,.15)" strokeWidth="2.5" />
          <text x="20" y="26" textAnchor="middle" fontSize="18" fontWeight="bold" fill="rgba(59,51,85,.55)">
            ¢
          </text>
        </svg>
      ))}
    </div>
  );
}

/** Big animated coin stack for empty states / fun. */
export function CoinStack({ size = 120 }: { size?: number }) {
  return (
    <svg viewBox="0 0 120 110" width={size} height={(size * 11) / 12} aria-hidden>
      {[
        { y: 82, w: 96, fill: "#D9A61F", anim: "" },
        { y: 62, w: 104, fill: "#EDBE3C", anim: "animate-float" },
        { y: 42, w: 100, fill: "#F5C445", anim: "" },
        { y: 22, w: 92, fill: "#F9D569", anim: "animate-float" },
      ].map((c, i) => (
        <g key={i} className={c.anim} style={i % 2 ? { animationDelay: `${i * 0.4}s` } : undefined}>
          <ellipse cx="60" cy={c.y} rx={c.w / 2} ry="12" fill={c.fill} stroke="#D9A61F" strokeWidth="2.5" />
          <ellipse cx="60" cy={c.y - 4} rx={(c.w - 16) / 2} ry="8" fill="#FBE49B" opacity="0.8" />
        </g>
      ))}
      <path d="M56 96 q8 8 16 0" fill="none" stroke="#D9A61F" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
