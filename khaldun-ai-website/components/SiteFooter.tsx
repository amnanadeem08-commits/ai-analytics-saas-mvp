import Link from "next/link";
import { nav, products, site } from "@/content/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10">
      <div className="mx-auto grid max-w-site gap-10 px-6 py-12 md:grid-cols-[1.2fr_1fr_1fr]">
        <div>
          <div className="font-display text-lg font-semibold text-paper">{site.name}</div>
          <p className="mt-3 max-w-sm text-sm text-muted">{site.tagline}</p>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Navigate</div>
          <ul className="mt-3 space-y-2 text-sm text-paper/80">
            {nav.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="hover:text-signal">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Products</div>
          <ul className="mt-3 space-y-2 text-sm text-paper/80">
            {products.map((product) => (
              <li key={product.id}>
                <Link href={product.href} className="hover:text-signal">
                  {product.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-site flex-col gap-2 px-6 py-4 font-mono text-[11px] text-muted sm:flex-row sm:justify-between">
          <span>© {new Date().getFullYear()} {site.name}</span>
          <a href={`mailto:${site.email}`} className="hover:text-paper">
            {site.email}
          </a>
        </div>
      </div>
    </footer>
  );
}
