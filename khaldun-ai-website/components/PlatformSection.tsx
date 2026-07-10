"use client";

import { motion, useReducedMotion } from "framer-motion";
import { platformScreens } from "@/content/site";

function ScreenMock({ id, title }: { id: string; title: string }) {
  // Product-inspired UI chrome — different layout per screen type
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-panel">
      <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
        <span className="h-1.5 w-1.5 rounded-full bg-signal/80" />
        <span className="font-mono text-[9px] uppercase tracking-wider text-muted">{title}</span>
      </div>
      <div className="space-y-2 p-3">
        {id === "dashboard" && (
          <>
            <div className="grid grid-cols-3 gap-1.5">
              {[1, 2, 3].map((n) => (
                <div key={n} className="rounded bg-ink/70 p-2">
                  <div className="h-1.5 w-8 rounded bg-muted/40" />
                  <div className="mt-2 h-4 w-10 rounded bg-signal/40" />
                </div>
              ))}
            </div>
            <div className="h-16 rounded bg-ink/60 p-2">
              <svg viewBox="0 0 120 40" className="h-full w-full">
                <polyline fill="none" stroke="#17D9C4" strokeWidth="1.5" points="0,30 20,22 40,26 60,14 80,18 100,8 120,12" />
              </svg>
            </div>
          </>
        )}
        {id === "report" && (
          <>
            <div className="h-3 w-2/3 rounded bg-paper/20" />
            <div className="h-2 w-full rounded bg-muted/30" />
            <div className="h-2 w-5/6 rounded bg-muted/25" />
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div className="h-12 rounded bg-ink/70" />
              <div className="h-12 rounded bg-ink/70" />
            </div>
          </>
        )}
        {id === "analyst" && (
          <>
            <div className="ml-auto max-w-[80%] rounded-lg bg-signal/15 px-2 py-1.5 text-[10px] text-paper/80">
              Why did margin drop in South?
            </div>
            <div className="max-w-[90%] rounded-lg bg-ink/70 px-2 py-1.5 text-[10px] text-muted">
              Discount mix rose 4pts while volume held — review promo depth.
            </div>
          </>
        )}
        {id === "upload" && (
          <div className="flex h-24 flex-col items-center justify-center rounded border border-dashed border-white/15 bg-ink/50">
            <div className="font-mono text-[10px] text-signal">CSV / XLSX</div>
            <div className="mt-1 text-[10px] text-muted">Drop file to profile</div>
          </div>
        )}
        {id === "workflow" && (
          <div className="space-y-1.5">
            {["Ingest", "Profile", "Analyze", "Evaluate"].map((s, i) => (
              <div key={s} className="flex items-center gap-2 rounded bg-ink/60 px-2 py-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${i < 3 ? "bg-signal" : "bg-muted"}`} />
                <span className="font-mono text-[10px] text-paper/70">{s}</span>
              </div>
            ))}
          </div>
        )}
        {id === "knowledge" && (
          <div className="space-y-1.5">
            {["Policy.pdf", "KPI glossary.docx", "Region notes.md"].map((f) => (
              <div key={f} className="rounded bg-ink/60 px-2 py-1.5 font-mono text-[10px] text-muted">
                {f}
              </div>
            ))}
          </div>
        )}
        {id === "evaluation" && (
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded bg-ink/70 p-2 text-center">
              <div className="font-display text-lg text-signal">82</div>
              <div className="font-mono text-[9px] text-muted">score</div>
            </div>
            <div className="rounded bg-ink/70 p-2 text-center">
              <div className="font-display text-lg text-amber">B+</div>
              <div className="font-mono text-[9px] text-muted">grade</div>
            </div>
          </div>
        )}
        {id === "storage" && (
          <div className="space-y-1.5">
            {["v3 current", "v2 archived", "v1 archived"].map((v) => (
              <div key={v} className="flex justify-between rounded bg-ink/60 px-2 py-1.5 font-mono text-[10px] text-muted">
                <span>{v}</span>
                <span className="text-signal/70">ok</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function PlatformSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="platform" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Platform</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            Show the platform
          </h2>
          <p className="mt-4 text-muted">
            Product-inspired screens — the same jobs your team will open after upload.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {platformScreens.map((screen, i) => (
            <motion.figure
              key={screen.id}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ delay: i * 0.03 }}
            >
              <ScreenMock id={screen.id} title={screen.title} />
              <figcaption className="mt-3">
                <div className="text-sm font-medium text-paper">{screen.title}</div>
                <p className="mt-1 text-xs leading-relaxed text-muted">{screen.caption}</p>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}
