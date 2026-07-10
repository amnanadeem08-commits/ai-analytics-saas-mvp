"use client";

import { motion, useReducedMotion } from "framer-motion";
import { whySteps } from "@/content/site";

export function WhySection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="why" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Why Khaldun AI</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            From problem to decision
          </h2>
          <p className="mt-4 text-muted">A simple path. No theatre.</p>
        </div>

        <ol className="mt-12 grid gap-0 md:grid-cols-6">
          {whySteps.map((step, i) => (
            <motion.li
              key={step.title}
              className="relative border-l border-white/10 pl-4 md:border-l-0 md:border-t md:pl-0 md:pt-4"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="absolute -left-[5px] top-0 h-2.5 w-2.5 rounded-full bg-signal md:left-0 md:top-[-5px]" />
              <div className="font-mono text-[10px] text-muted">{String(i + 1).padStart(2, "0")}</div>
              <div className="mt-2 pr-3 font-display text-base font-semibold text-paper">{step.title}</div>
              <p className="mt-1 pr-3 text-xs text-muted">{step.detail}</p>
              {i < whySteps.length - 1 && (
                <span className="mt-3 hidden font-mono text-[10px] text-signal/50 md:block" aria-hidden>
                  ↓
                </span>
              )}
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
