"use client";

import type { CSSProperties } from "react";

type Props = {
  size?: number;
  /** Modo cientifico: aparecen los lentes. */
  glasses?: boolean;
  /** Pensando o respondiendo: la antena brilla y la boca se mueve. */
  active?: boolean;
  style?: CSSProperties;
};

const STROKE = "#1d2433";

/** Astro: robot con casco espacial y antenita. Dibujo propio, sin imagenes externas. */
export default function Robot({ size = 56, glasses = false, active = false, style }: Props) {
  return (
    <svg viewBox="0 0 120 120" width={size} height={size} role="img" aria-label="Robot asistente" style={style}>
      <style>{`
        @keyframes eter-glow { 0%,100% { opacity: 1; r: 5px; } 50% { opacity: .45; r: 7px; } }
        @keyframes eter-talk { 0%,100% { transform: scaleY(1); } 50% { transform: scaleY(1.9); } }
        @keyframes eter-blink { 0%,92%,100% { transform: scaleY(1); } 96% { transform: scaleY(.1); } }
        .eter-tip-on { animation: eter-glow .7s ease-in-out infinite; }
        .eter-mouth-on { animation: eter-talk .35s ease-in-out infinite; transform-origin: 60px 80px; }
        .eter-eye { animation: eter-blink 5s infinite; transform-origin: center; transform-box: fill-box; }
        .eter-glasses { transition: transform .45s cubic-bezier(.2,1.4,.4,1), opacity .3s; }
        @media (prefers-reduced-motion: reduce) { .eter-tip-on, .eter-mouth-on, .eter-eye { animation: none; } }
      `}</style>

      {/* antena */}
      <line x1="60" y1="22" x2="60" y2="10" stroke="#5b6b8c" strokeWidth="4" strokeLinecap="round" />
      <circle cx="60" cy="8" r="5" fill="#ff9f43" className={active ? "eter-tip-on" : undefined} />

      {/* casco y cara */}
      <circle cx="60" cy="66" r="42" fill="#f4f6fb" stroke="#5b6b8c" strokeWidth="4" />
      <ellipse cx="60" cy="68" rx="31" ry="27" fill="#1d2a4a" />
      <ellipse cx="50" cy="58" rx="10" ry="5" fill="#fff" opacity=".25" transform="rotate(-25 50 58)" />

      {/* ojos y boca */}
      <circle cx="50" cy="70" r="5" fill="#9be7a8" className="eter-eye" />
      <circle cx="70" cy="70" r="5" fill="#9be7a8" className="eter-eye" />
      <path
        d="M54 81 q6 5 12 0"
        fill="none"
        stroke="#9be7a8"
        strokeWidth="3"
        strokeLinecap="round"
        className={active ? "eter-mouth-on" : undefined}
      />

      {/* lentes (modo cientifico) */}
      <g
        className="eter-glasses"
        style={{ opacity: glasses ? 1 : 0, transform: glasses ? "translateY(0)" : "translateY(-14px)" }}
        aria-hidden={!glasses}
      >
        <circle cx="50" cy="70" r="10.5" fill="rgba(255,255,255,.2)" stroke="#fff" strokeWidth="3" />
        <circle cx="70" cy="70" r="10.5" fill="rgba(255,255,255,.2)" stroke="#fff" strokeWidth="3" />
        <path d="M60.5 70 h-1" stroke="#fff" strokeWidth="3" />
        <path d="M39.5 70 l-6 -3 M80.5 70 l6 -3" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
      </g>
    </svg>
  );
}
