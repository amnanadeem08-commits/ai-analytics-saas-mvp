"use client";

import { motion, useReducedMotion } from "framer-motion";
import { contact, site } from "@/content/site";

export function ContactSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="contact" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-20">
        <motion.div
          className="rounded-2xl border border-white/10 bg-panel p-8 md:p-10"
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.35 }}
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">contact</p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            {contact.title}
          </h2>
          <p className="mt-4 max-w-2xl text-muted">{contact.body}</p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href={contact.mailto}
              className="inline-flex rounded-md bg-amber px-5 py-2.5 text-sm font-medium text-ink transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
            >
              {contact.ctaLabel}
            </a>
            <a
              href={`mailto:${site.email}`}
              className="font-mono text-sm text-signal underline-offset-4 hover:underline"
            >
              {site.email}
            </a>
          </div>

          <div className="mt-8 flex flex-wrap gap-4 border-t border-white/10 pt-6 font-mono text-xs text-muted">
            <a
              href={site.links.fiverr}
              target="_blank"
              rel="noreferrer"
              className="transition hover:text-paper"
            >
              Fiverr {/* TODO: replace with real profile URL */}
            </a>
            <a
              href={site.links.upwork}
              target="_blank"
              rel="noreferrer"
              className="transition hover:text-paper"
            >
              Upwork {/* TODO: replace with real profile URL */}
            </a>
            <a
              href={site.links.linkedin}
              target="_blank"
              rel="noreferrer"
              className="transition hover:text-paper"
            >
              LinkedIn {/* TODO: replace with real profile URL */}
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
