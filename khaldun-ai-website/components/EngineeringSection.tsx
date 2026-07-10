"use client";

import { motion, useInView, useMotionValue, useSpring, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";
import { engineeringCapabilities, engineeringMetrics } from "@/content/site";

function Counter({ value, suffix }: { value: number; suffix: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const reduceMotion = useReducedMotion();
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 60, damping: 20 });

  useEffect(() => {
    if (inView) motionValue.set(value);
  }, [inView, motionValue, value]);

  useEffect(() => {
    if (reduceMotion && ref.current) {
      ref.current.textContent = `${value}${suffix}`;
      return;
    }
    return spring.on("change", (latest) => {
      if (ref.current) ref.current.textContent = `${Math.round(latest)}${suffix}`;
    });
  }, [spring, reduceMotion, value, suffix]);

  return (
    <span ref={ref} className="font-display text-4xl font-semibold tracking-tight text-paper md:text-5xl">
      {reduceMotion ? `${value}${suffix}` : `0${suffix}`}
    </span>
  );
}

export function EngineeringSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="engineering" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Engineering</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            Built like production software.
          </h2>
          <p className="mt-4 text-lg text-muted">Real engineering behind every workflow.</p>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {engineeringMetrics.map((m, i) => (
            <motion.div
              key={m.label}
              className="rounded-2xl border border-white/10 bg-panel p-6 md:p-8"
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
            >
              <Counter value={m.value} suffix={m.suffix} />
              <div className="mt-2 font-mono text-xs uppercase tracking-[0.14em] text-muted">{m.label}</div>
            </motion.div>
          ))}
        </div>

        <ul className="mt-8 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {engineeringCapabilities.map((cap, i) => (
            <motion.li
              key={cap}
              className="rounded-lg border border-white/8 bg-ink/40 px-4 py-3 font-mono text-xs text-paper/80"
              initial={reduceMotion ? false : { opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.05 + i * 0.02 }}
            >
              <span className="mr-2 text-signal">▸</span>
              {cap}
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
