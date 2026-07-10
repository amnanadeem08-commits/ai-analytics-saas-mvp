"use client";

import { motion, useReducedMotion } from "framer-motion";
import { proof } from "@/content/site";

export function ProofSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="proof" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-20">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.35 }}
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">credibility</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            {proof.title}
          </h2>
          <p className="mt-3 max-w-2xl rounded-md border border-amber/30 bg-amber/5 px-3 py-2 font-mono text-xs text-amber">
            {proof.note}
          </p>
        </motion.div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {proof.placeholders.map((slot, index) => (
            <motion.div
              key={slot.label}
              className="rounded-xl border border-dashed border-white/15 bg-panel/40 p-5"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.35, delay: index * 0.05 }}
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">placeholder</div>
              <h3 className="mt-2 font-display text-lg text-paper">{slot.label}</h3>
              <p className="mt-2 text-sm text-muted">{slot.detail}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
