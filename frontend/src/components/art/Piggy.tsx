/**
 * Penny the Piggy — the Mommy Bank mascot, hand-drawn in SVG.
 * Moods: happy | wow | sleepy | celebrate | think
 */
type Mood = "happy" | "wow" | "sleepy" | "celebrate" | "think";

interface PiggyProps {
  mood?: Mood;
  size?: number;
  className?: string;
  animate?: boolean;
}

export function Piggy({ mood = "happy", size = 140, className = "", animate = true }: PiggyProps) {
  const float = animate ? "animate-float" : "";
  return (
    <svg
      viewBox="0 0 200 170"
      width={size}
      height={(size * 17) / 20}
      className={`${float} ${className}`}
      role="img"
      aria-label={`Penny the piggy, ${mood}`}
    >
      <defs>
        <radialGradient id="pg-body" cx="38%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#FBC4DD" />
          <stop offset="100%" stopColor="#F49BC6" />
        </radialGradient>
        <linearGradient id="pg-snout" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F7A9CC" />
          <stop offset="100%" stopColor="#EE85B7" />
        </linearGradient>
      </defs>

      {/* shadow */}
      <ellipse cx="100" cy="152" rx="62" ry="10" fill="#3B3355" opacity="0.10" />

      {/* tail */}
      <path
        d="M162 108 q16 -4 12 8 q-4 10 -14 6 q-8 -3 -3 -9"
        fill="none"
        stroke="#EE85B7"
        strokeWidth="7"
        strokeLinecap="round"
      />

      {/* legs */}
      <rect x="62" y="126" width="18" height="22" rx="9" fill="#EE85B7" />
      <rect x="120" y="126" width="18" height="22" rx="9" fill="#EE85B7" />

      {/* ears */}
      <path d="M56 44 q-4 -22 14 -24 q10 -1 10 14 l-1 10 z" fill="#EE85B7" />
      <path d="M144 44 q4 -22 -14 -24 q-10 -1 -10 14 l1 10 z" fill="#EE85B7" />

      {/* body */}
      <ellipse cx="100" cy="90" rx="64" ry="54" fill="url(#pg-body)" />
      {/* belly highlight */}
      <ellipse cx="84" cy="78" rx="34" ry="24" fill="#FDD9EA" opacity="0.7" />

      {/* coin slot + coin (bank-ness) */}
      <rect x="86" y="36" width="28" height="7" rx="3.5" fill="#D9719F" />
      {mood === "celebrate" && (
        <g className="animate-drop">
          <circle cx="100" cy="20" r="11" fill="#F5C445" stroke="#D9A61F" strokeWidth="3" />
          <text x="100" y="25" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#D9A61F">
            $
          </text>
        </g>
      )}

      {/* eyes */}
      {mood === "sleepy" ? (
        <>
          <path d="M64 82 q7 7 14 0" fill="none" stroke="#3B3355" strokeWidth="4" strokeLinecap="round" />
          <path d="M122 82 q7 7 14 0" fill="none" stroke="#3B3355" strokeWidth="4" strokeLinecap="round" />
          <text x="158" y="52" fontSize="16" fontWeight="bold" fill="#A78BFA" className="animate-sparkle">
            z
          </text>
          <text x="170" y="36" fontSize="12" fontWeight="bold" fill="#A78BFA" className="animate-sparkle">
            z
          </text>
        </>
      ) : (
        <>
          <circle cx="71" cy="84" r="6.5" fill="#3B3355" />
          <circle cx="129" cy="84" r="6.5" fill="#3B3355" />
          <circle cx="73.5" cy="81.5" r="2.2" fill="#fff" />
          <circle cx="131.5" cy="81.5" r="2.2" fill="#fff" />
        </>
      )}
      {mood === "think" && (
        <path d="M118 72 q6 -6 12 -2" fill="none" stroke="#3B3355" strokeWidth="3.5" strokeLinecap="round" />
      )}

      {/* snout */}
      <ellipse cx="100" cy="100" rx="21" ry="15" fill="url(#pg-snout)" />
      <ellipse cx="92" cy="100" rx="3.4" ry="4.6" fill="#C2548D" />
      <ellipse cx="108" cy="100" rx="3.4" ry="4.6" fill="#C2548D" />

      {/* mouth */}
      {mood === "wow" ? (
        <ellipse cx="100" cy="120" rx="7" ry="9" fill="#B4437B" />
      ) : mood === "celebrate" ? (
        <path d="M90 118 q10 12 20 0 q-10 4 -20 0z" fill="#B4437B" />
      ) : mood === "happy" ? (
        <path d="M92 117 q8 7 16 0" fill="none" stroke="#3B3355" strokeWidth="3.5" strokeLinecap="round" />
      ) : null}

      {/* blush */}
      <ellipse cx="56" cy="98" rx="9" ry="5.5" fill="#F27DAE" opacity="0.55" />
      <ellipse cx="144" cy="98" rx="9" ry="5.5" fill="#F27DAE" opacity="0.55" />

      {/* party hat for celebrate */}
      {mood === "celebrate" && (
        <g>
          <path d="M100 -2 L88 30 L112 30 Z" fill="#63C9A8" />
          <circle cx="100" cy="-2" r="4" fill="#F5C445" />
          <circle cx="96" cy="16" r="2.5" fill="#fff" opacity="0.8" />
          <circle cx="105" cy="22" r="2" fill="#fff" opacity="0.8" />
        </g>
      )}
      {/* thought dots for think */}
      {mood === "think" && (
        <g fill="#A78BFA" className="animate-sparkle">
          <circle cx="158" cy="56" r="3" />
          <circle cx="167" cy="44" r="4.5" />
          <circle cx="178" cy="30" r="6.5" />
        </g>
      )}
    </svg>
  );
}

/** Small flat piggy face used as logo/avatar. */
export function PigFace({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={className} aria-hidden>
      <ellipse cx="32" cy="34" rx="26" ry="23" fill="#F49BC6" />
      <path d="M14 20 q-2 -10 7 -10 q6 0 5 8 z" fill="#EE85B7" />
      <path d="M50 20 q2 -10 -7 -10 q-6 0 -5 8 z" fill="#EE85B7" />
      <circle cx="24" cy="30" r="3.2" fill="#3B3355" />
      <circle cx="40" cy="30" r="3.2" fill="#3B3355" />
      <ellipse cx="32" cy="40" rx="10" ry="7.5" fill="#EE85B7" />
      <ellipse cx="28" cy="40" rx="1.8" ry="2.6" fill="#C2548D" />
      <ellipse cx="36" cy="40" rx="1.8" ry="2.6" fill="#C2548D" />
      <ellipse cx="15" cy="38" rx="4.5" ry="3" fill="#F27DAE" opacity="0.6" />
      <ellipse cx="49" cy="38" rx="4.5" ry="3" fill="#F27DAE" opacity="0.6" />
    </svg>
  );
}
