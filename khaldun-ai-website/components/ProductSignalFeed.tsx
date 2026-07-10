"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import type { Product } from "@/content/site";
import { products } from "@/content/site";

function StatusTag({ product }: { product: Product }) {
  const tone =
    product.status === "labs"
      ? "border-signal/40 text-signal"
      : product.status === "coming-soon"
        ? "border-white/20 text-muted"
        : "border-amber/40 text-amber";

  return (
    <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] ${tone}`}>
      {product.statusLabel}
    </span>
  );
}

function ProductRow({ product, index }: { product: Product; index: number }) {
  const reduceMotion = useReducedMotion();
  const isLink = product.status !== "coming-soon";

  const body = (
    <>
      <div className="min-w-0 flex-1">
        <div className="font-display text-lg font-semibold tracking-tight text-paper sm:text-xl">
          {product.name}
        </div>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">{product.value}</p>
      </div>
      <div className="flex shrink-0 items-center gap-3 self-start sm:self-center">
        <StatusTag product={product} />
        {isLink && (
          <span className="font-mono text-[11px] text-paper/40 transition group-hover:text-signal">
            Learn more →
          </span>
        )}
      </div>
    </>
  );

  const className =
    "group flex flex-col gap-3 border-b border-white/10 py-5 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:px-1";

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
    >
      {isLink ? (
        <Link href={product.href} className={className}>
          {body}
        </Link>
      ) : (
        <div className={className}>{body}</div>
      )}
    </motion.div>
  );
}

export function ProductSignalFeed() {
  return (
    <section id="products" className="border-b border-white/10">
      <div className="mx-auto max-w-site px-6 py-16 md:py-24">
        <div className="mb-10 max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Products</p>
          <h2 className="mt-3 font-display text-3xl font-semibold tracking-tightest text-paper md:text-4xl">
            What we build
          </h2>
          <p className="mt-4 text-muted">
            Each line is a product with a clear job. Status tags mean what they say.
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-panel/70 px-4 sm:px-6">
          <div className="flex items-center justify-between border-b border-white/10 py-3 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
            <span>signal feed</span>
            <span>{products.length} products</span>
          </div>
          {products.map((product, index) => (
            <ProductRow key={product.id} product={product} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
