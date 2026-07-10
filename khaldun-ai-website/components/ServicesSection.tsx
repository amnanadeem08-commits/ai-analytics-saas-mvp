"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { services } from "@/content/site";

export function ServicesSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="services" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Services</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            Work we deliver
          </h2>
          <p className="mt-4 text-muted">
            Project engagements for teams that need a dashboard, model, or automation — not a pitch deck.
          </p>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((service, i) => (
            <motion.article
              key={service.title}
              className="group rounded-2xl border border-white/10 bg-panel p-5 transition hover:border-signal/30"
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.03 }}
            >
              <div
                className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-ink font-mono text-xs text-signal"
                aria-hidden
              >
                {String(i + 1).padStart(2, "0")}
              </div>
              <h3 className="font-display text-lg font-semibold text-paper">{service.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{service.body}</p>
              <Link
                href="/#contact"
                className="mt-4 inline-flex font-mono text-[11px] text-signal opacity-80 transition group-hover:opacity-100"
              >
                Learn more →
              </Link>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
