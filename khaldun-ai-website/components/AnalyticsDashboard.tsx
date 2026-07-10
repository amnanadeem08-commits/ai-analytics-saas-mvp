"use client";

import { motion, useReducedMotion } from "framer-motion";

/** Realistic BI dashboard mock — product-inspired, not stock photography. */
export function AnalyticsDashboard({ className = "" }: { className?: string }) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      className={`overflow-hidden rounded-2xl border border-white/10 bg-panel shadow-[0_24px_80px_-40px_rgba(23,217,196,0.35)] ${className}`}
      role="img"
      aria-label="Sample analytics dashboard with KPI cards, charts, and an AI insight panel"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-signal" aria-hidden />
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
            AI Data Bot · sample workspace
          </span>
        </div>
        <span className="font-mono text-[10px] text-paper/50">Sales · Q2</span>
      </div>

      <div className="space-y-3 p-3 sm:p-4">
        {/* KPI row */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { label: "Revenue", value: "2.84M", delta: "+6.2%", up: true },
            { label: "Orders", value: "18.4K", delta: "+3.1%", up: true },
            { label: "Margin", value: "24.8%", delta: "−0.4%", up: false },
            { label: "NPS", value: "62", delta: "+2", up: true },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg border border-white/8 bg-ink/60 p-2.5">
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted">{kpi.label}</div>
              <div className="mt-1 font-display text-lg font-semibold text-paper sm:text-xl">{kpi.value}</div>
              <div className={`font-mono text-[10px] ${kpi.up ? "text-signal" : "text-amber"}`}>{kpi.delta}</div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
          {/* Line chart */}
          <div className="rounded-lg border border-white/8 bg-ink/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-paper/80">Revenue trend</span>
              <span className="font-mono text-[9px] text-muted">12 periods</span>
            </div>
            <svg viewBox="0 0 320 110" className="h-auto w-full" aria-hidden>
              <defs>
                <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#17D9C4" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="#17D9C4" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[30, 55, 80].map((y) => (
                <line key={y} x1="0" x2="320" y1={y} y2={y} stroke="rgba(237,239,244,0.06)" />
              ))}
              <motion.path
                d="M0 78 L30 70 L60 74 L90 58 L120 62 L150 48 L180 52 L210 40 L240 44 L270 32 L300 36 L320 28"
                fill="none"
                stroke="#17D9C4"
                strokeWidth="2"
                initial={reduceMotion ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.2, ease: "easeInOut" }}
              />
              <motion.path
                d="M0 78 L30 70 L60 74 L90 58 L120 62 L150 48 L180 52 L210 40 L240 44 L270 32 L300 36 L320 28 L320 110 L0 110 Z"
                fill="url(#revFill)"
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5, duration: 0.6 }}
              />
            </svg>
          </div>

          {/* Bar + forecast */}
          <div className="grid gap-3">
            <div className="rounded-lg border border-white/8 bg-ink/50 p-3">
              <div className="mb-2 text-xs text-paper/80">Orders by region</div>
              <div className="flex h-16 items-end gap-1.5">
                {[40, 65, 48, 80, 55, 70].map((h, i) => (
                  <motion.div
                    key={i}
                    className="flex-1 rounded-sm bg-signal/80"
                    initial={reduceMotion ? false : { height: 0 }}
                    animate={{ height: `${h}%` }}
                    transition={{ duration: 0.6, delay: 0.15 + i * 0.05 }}
                  />
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-amber/25 bg-amber/5 p-3">
              <div className="font-mono text-[9px] uppercase tracking-wider text-amber">Forecast</div>
              <div className="mt-1 text-sm text-paper">Next period outlook: steady growth</div>
              <div className="mt-1 font-mono text-[10px] text-muted">Sample projection · not a guarantee</div>
            </div>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_1.1fr]">
          {/* Sparkline card */}
          <div className="rounded-lg border border-white/8 bg-ink/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-paper/80">Conversion sparkline</span>
              <span className="font-mono text-[10px] text-signal">3.8%</span>
            </div>
            <svg viewBox="0 0 200 36" className="mt-2 h-8 w-full" aria-hidden>
              <motion.polyline
                fill="none"
                stroke="#F2A93B"
                strokeWidth="1.5"
                points="0,28 20,24 40,26 60,18 80,20 100,14 120,16 140,10 160,12 180,8 200,9"
                initial={reduceMotion ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, delay: 0.3 }}
              />
            </svg>
          </div>

          {/* AI insight */}
          <div className="rounded-lg border border-signal/25 bg-signal/5 p-3">
            <div className="font-mono text-[9px] uppercase tracking-wider text-signal">AI insight</div>
            <p className="mt-1.5 text-sm leading-snug text-paper/90">
              South region orders rose while margin dipped slightly — review discount mix before the next campaign.
            </p>
            <div className="mt-2 font-mono text-[10px] text-muted">Executive summary · sample</div>
          </div>
        </div>
      </div>
    </div>
  );
}
