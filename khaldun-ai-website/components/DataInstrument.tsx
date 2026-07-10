"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";

type Point = { x: number; y: number };

function buildPath(points: Point[]): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
}

function series(seed: number[], width: number, height: number, pad = 12): Point[] {
  const min = Math.min(...seed);
  const max = Math.max(...seed);
  const span = max - min || 1;
  return seed.map((v, i) => ({
    x: pad + (i / (seed.length - 1)) * (width - pad * 2),
    y: pad + (1 - (v - min) / span) * (height - pad * 2),
  }));
}

const KPI_SEED = [42, 45, 44, 51, 49, 58, 55, 63, 61, 70, 68, 74];
const PRICE_SEED = [28, 31, 29, 36, 34, 33, 40, 38, 45, 43, 48, 52];

export function DataInstrument({ className = "" }: { className?: string }) {
  const reduceMotion = useReducedMotion();
  const width = 420;
  const height = 240;

  const kpi = useMemo(() => series(KPI_SEED, width, height - 40), []);
  const price = useMemo(() => series(PRICE_SEED, width, height - 40), []);
  const kpiPath = buildPath(kpi);
  const pricePath = buildPath(price);

  const candles = useMemo(() => {
    const base = [30, 34, 32, 38, 36, 41, 39, 44, 42, 47, 45, 50];
    return base.map((close, i) => {
      const open = close - (i % 2 === 0 ? 4 : -3);
      const high = Math.max(open, close) + 3;
      const low = Math.min(open, close) - 3;
      const x = 18 + (i / (base.length - 1)) * (width - 36);
      const scale = (v: number) => 18 + (1 - (v - 24) / 32) * (height - 70);
      return {
        x,
        open: scale(open),
        close: scale(close),
        high: scale(high),
        low: scale(low),
        up: close >= open,
      };
    });
  }, []);

  const drawDuration = reduceMotion ? 0 : 1.4;

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-white/10 bg-panel shadow-[0_0_0_1px_rgba(23,217,196,0.08)] ${className}`}
      aria-label="Animated data instrument showing KPI sparkline and mock candlesticks"
      role="img"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-signal" aria-hidden />
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
            instrument · idle
          </span>
        </div>
        <span className="font-mono text-[10px] text-signal">KPI + OHLC</span>
      </div>

      <div className="grid grid-cols-3 gap-2 border-b border-white/5 px-4 py-3 font-mono text-[11px]">
        <div>
          <div className="text-muted">REV.IDX</div>
          <div className="text-amber">74.2</div>
        </div>
        <div>
          <div className="text-muted">Δ 12P</div>
          <div className="text-signal">+8.4%</div>
        </div>
        <div>
          <div className="text-muted">SIGNAL</div>
          <div className="text-paper">WATCH</div>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="kpiFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#17D9C4" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#17D9C4" stopOpacity="0" />
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75].map((t) => (
          <line
            key={t}
            x1="12"
            x2={width - 12}
            y1={20 + t * (height - 60)}
            y2={20 + t * (height - 60)}
            stroke="rgba(237,239,244,0.06)"
            strokeWidth="1"
          />
        ))}

        {candles.map((c, i) => (
          <g key={i} opacity={0.55}>
            <line
              x1={c.x}
              x2={c.x}
              y1={c.high}
              y2={c.low}
              stroke={c.up ? "#17D9C4" : "#6B7280"}
              strokeWidth="1"
            />
            <rect
              x={c.x - 4}
              y={Math.min(c.open, c.close)}
              width="8"
              height={Math.max(2, Math.abs(c.close - c.open))}
              fill={c.up ? "#17D9C4" : "#6B7280"}
              opacity={0.7}
            />
          </g>
        ))}

        <motion.path
          d={`${kpiPath} L ${kpi[kpi.length - 1].x} ${height - 28} L ${kpi[0].x} ${height - 28} Z`}
          fill="url(#kpiFill)"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: drawDuration * 0.6, delay: reduceMotion ? 0 : 0.6 }}
        />

        <motion.path
          d={pricePath}
          fill="none"
          stroke="#6B7280"
          strokeWidth="1.5"
          strokeLinecap="round"
          initial={reduceMotion ? false : { pathLength: 0, opacity: 0.4 }}
          animate={{ pathLength: 1, opacity: 0.55 }}
          transition={{ duration: drawDuration, ease: "easeInOut" }}
        />

        <motion.path
          d={kpiPath}
          fill="none"
          stroke="#17D9C4"
          strokeWidth="2"
          strokeLinecap="round"
          initial={reduceMotion ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: drawDuration, ease: "easeInOut", delay: reduceMotion ? 0 : 0.15 }}
        />

        {!reduceMotion && (
          <motion.circle
            r="3.5"
            fill="#F2A93B"
            initial={{ opacity: 0 }}
            animate={{
              opacity: [0.4, 1, 0.4],
              cx: kpi[kpi.length - 1].x,
              cy: kpi[kpi.length - 1].y,
            }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut", delay: drawDuration }}
          />
        )}

        <text x="16" y={height - 10} className="fill-muted" style={{ fontSize: 10, fontFamily: "var(--font-mono)" }}>
          MOCK SERIES · NOT LIVE MARKET DATA
        </text>
      </svg>
    </div>
  );
}
