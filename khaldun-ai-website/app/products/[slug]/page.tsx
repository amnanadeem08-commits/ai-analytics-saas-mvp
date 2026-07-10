import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { products, type Product } from "@/content/site";

type Params = { slug: string };

const bySlug = Object.fromEntries(products.map((p) => [p.id, p])) as Record<string, Product>;

export function generateStaticParams(): Params[] {
  return products.map((p) => ({ slug: p.id }));
}

export function generateMetadata({ params }: { params: Params }): Metadata {
  const product = bySlug[params.slug];
  if (!product) return { title: "Product" };
  return {
    title: product.name,
    description: product.value,
  };
}

export default function ProductPage({ params }: { params: Params }) {
  const product = bySlug[params.slug];
  if (!product) notFound();

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="mx-auto max-w-site px-6 py-16 md:py-20">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Product</p>
        <h1 className="mt-4 font-display text-4xl font-semibold tracking-tightest text-paper md:text-5xl">
          {product.name}
        </h1>
        <p className="mt-2 font-mono text-xs text-amber">{product.statusLabel}</p>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">{product.value}</p>

        <div className="mt-10 rounded-xl border border-dashed border-white/15 bg-panel/50 p-6">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Detail page</p>
          <p className="mt-2 text-sm text-muted">
            Full product page content will expand here. This stub keeps navigation and static export working.
          </p>
        </div>

        <Link href="/#products" className="mt-10 inline-flex text-sm text-signal underline-offset-4 hover:underline">
          ← Back to products
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
