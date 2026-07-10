"use client";

import { motion, useReducedMotion } from "framer-motion";
import { contact, faq, site } from "@/content/site";

export function ContactSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section id="contact" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
          <motion.div
            className="rounded-2xl border border-white/10 bg-panel p-8 md:p-10"
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Contact</p>
            <h2 className="mt-3 max-w-xl font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
              {contact.title}
            </h2>
            <p className="mt-4 max-w-xl text-muted">{contact.body}</p>

            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href={contact.mailto}
                className="inline-flex rounded-md bg-amber px-5 py-2.5 text-sm font-medium text-ink transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
              >
                {contact.ctaLabel}
              </a>
              <a
                href={site.links.booking}
                className="inline-flex rounded-md border border-white/15 px-5 py-2.5 text-sm text-paper transition hover:border-white/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
              >
                {contact.demoLabel}
              </a>
            </div>

            <dl className="mt-10 grid gap-4 border-t border-white/10 pt-8 sm:grid-cols-2">
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-wider text-muted">Email</dt>
                <dd className="mt-1">
                  <a href={`mailto:${site.email}`} className="text-signal hover:underline">
                    {site.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-wider text-muted">Business hours</dt>
                <dd className="mt-1 text-sm text-paper/80">{site.businessHours}</dd>
              </div>
            </dl>

            <div className="mt-6 flex flex-wrap gap-4 font-mono text-xs text-muted">
              <a href={site.links.linkedin} target="_blank" rel="noreferrer" className="hover:text-paper">
                LinkedIn {/* TODO: real URL */}
              </a>
              <a href={site.links.github} target="_blank" rel="noreferrer" className="hover:text-paper">
                GitHub
              </a>
              <a href={site.links.fiverr} target="_blank" rel="noreferrer" className="hover:text-paper">
                Fiverr {/* TODO: real URL */}
              </a>
              <a href={site.links.upwork} target="_blank" rel="noreferrer" className="hover:text-paper">
                Upwork {/* TODO: real URL */}
              </a>
            </div>
          </motion.div>

          <motion.div
            id="faq"
            className="rounded-2xl border border-white/10 bg-ink/40 p-6 md:p-8"
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.05 }}
          >
            <h3 className="font-display text-xl font-semibold text-paper">FAQ</h3>
            <ul className="mt-6 space-y-5">
              {faq.map((item) => (
                <li key={item.q}>
                  <div className="text-sm font-medium text-paper">{item.q}</div>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.a}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
