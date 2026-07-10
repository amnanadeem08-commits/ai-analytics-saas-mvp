"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import type { Product } from "@/content/site";
import { futureProducts, products } from "@/content/site";

function StatusTag({ product }: { product: Product }) {
  const tone =
    product.status === "signal-only"
      ? "border-amber/40 text-amber"
      : product.status === "coming-next"
        ? "border-white/15 text-muted"
        : "border-signal/40 text-signal";

  return (
    <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] ${tone}`}>
      {product.statusLabel}
    </span>
  );
}

function ProductRow({ product, index }: { product: Product; index: number }) {
  const reduceMotion = useReducedMotion();
  const inner = (
    <>
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-baseline sm:gap-6">
        <span className="shrink-0 font-mono text-[11px] text-muted">{product.code} · {product.tagline}</span>
        <div className="min-w-0">
          <div className="font-display text-lg font-semibold tracking-tight text-paper">{product.name}</div>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">{product.description}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <StatusTag product={product} />
        {product.status !== "coming-next" && (
          <span className="font-mono text-[11px] text-paper/50 transition group-hover:text-signal">open →</span>
        )}
      </div>
    </>
  );

  const className =
    "group flex flex-col gap-4 border-b border-white/10 px-1 py-5 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:justify-between sm:gap-8";

  if (product.status === "coming-next") {
    return (
      <motion.div
        className={className}
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.35, delay: index * 0.05 }}
      >
        {inner}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.4 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
    >
      <Link href={product.href} className={className}>
        {inner}
      </Link>
    </motion.div>
  );
}

export function ProductSignalFeed() {
  const rows = [...products, ...futureProducts];

  return (
    <section id="products" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-20">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">product feed</p>
            <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
              What we ship
            </h2>
          </div>
          <p className="max-w-md text-sm text-muted">
            Read like a terminal log — each line is a product with a clear status. No fake “LIVE” tags.
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-panel/60 px-4 sm:px-5">
          <div className="flex items-center justify-between border-b border-white/10 py-3 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
            <span>channel · products</span>
            <span>{rows.length} entries</span>
          </div>
          {rows.map((product, index) => (
            <ProductRow key={product.id} product={product} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
