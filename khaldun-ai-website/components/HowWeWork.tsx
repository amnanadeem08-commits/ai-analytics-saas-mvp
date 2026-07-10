"use client";

import { motion, useReducedMotion } from "framer-motion";
import { howWeWork } from "@/content/site";

export function HowWeWork() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="how-we-work" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-20">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.35 }}
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">method</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            {howWeWork.title}
          </h2>
          <p className="mt-3 max-w-2xl text-muted">{howWeWork.lead}</p>
        </motion.div>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {howWeWork.items.map((item, index) => (
            <motion.article
              key={item.title}
              className="rounded-xl border border-white/10 bg-panel p-6"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.35, delay: index * 0.06 }}
            >
              <h3 className="font-display text-xl font-semibold text-paper">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted">{item.body}</p>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
