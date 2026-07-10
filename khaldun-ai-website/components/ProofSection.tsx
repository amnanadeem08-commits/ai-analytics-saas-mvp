"use client";

import { motion, useReducedMotion } from "framer-motion";
import { industries, milestones } from "@/content/site";

export function ProofSection() {
  const reduceMotion = useReducedMotion();
  const blocks = [milestones.dataBot, milestones.excel, milestones.coming];

  return (
    <section id="proof" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Proof</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            Product milestones
          </h2>
          <p className="mt-4 text-muted">
            Shipped capability — not invented customer quotes.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {blocks.map((block, i) => (
            <motion.article
              key={block.title}
              className="relative rounded-2xl border border-white/10 bg-panel p-6"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-amber">
                Milestone {String(i + 1).padStart(2, "0")}
              </div>
              <h3 className="mt-3 font-display text-xl font-semibold text-paper">{block.title}</h3>
              <ul className="mt-4 space-y-2">
                {block.items.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-muted">
                    <span className="text-signal">—</span>
                    {item}
                  </li>
                ))}
              </ul>
            </motion.article>
          ))}
        </div>

        <div className="mt-10 rounded-2xl border border-dashed border-white/15 bg-ink/30 p-6">
          <h3 className="font-display text-lg text-paper">Client case studies</h3>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Industry tracks we work in. Named case studies appear here only with client permission —
            we do not invent testimonials.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {industries.map((ind) => (
              <span
                key={ind}
                className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] text-paper/70"
              >
                {ind}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
