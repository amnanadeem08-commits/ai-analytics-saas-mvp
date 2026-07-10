import Link from "next/link";
import { nav, products, services, site } from "@/content/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-ink">
      <div className="mx-auto grid max-w-site gap-10 px-6 py-14 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div className="font-display text-lg font-semibold text-paper">{site.name}</div>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted">{site.tagline}</p>
          <a href={`mailto:${site.email}`} className="mt-4 inline-block font-mono text-xs text-signal">
            {site.email}
          </a>
        </div>

        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Products</div>
          <ul className="mt-3 space-y-2 text-sm text-paper/75">
            {products.map((p) => (
              <li key={p.id}>
                <Link href={p.href} className="hover:text-signal">
                  {p.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Services</div>
          <ul className="mt-3 space-y-2 text-sm text-paper/75">
            {services.slice(0, 6).map((s) => (
              <li key={s.title}>
                <Link href="/#services" className="hover:text-signal">
                  {s.title}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-8">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Company</div>
            <ul className="mt-3 space-y-2 text-sm text-paper/75">
              {nav.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="hover:text-signal">
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <Link href="/#faq" className="hover:text-signal">
                  FAQ
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Resources</div>
            <ul className="mt-3 space-y-2 text-sm text-paper/75">
              <li>
                <a href={site.links.github} target="_blank" rel="noreferrer" className="hover:text-signal">
                  Engineering / GitHub
                </a>
              </li>
              <li>
                <Link href="/#engineering" className="hover:text-signal">
                  Documentation highlights
                </Link>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-site flex-col gap-3 px-6 py-5 font-mono text-[11px] text-muted sm:flex-row sm:items-center sm:justify-between">
          <span>© {new Date().getFullYear()} {site.name}</span>
          <div className="flex flex-wrap gap-4">
            <span className="text-paper/40">Privacy · Terms — coming soon</span>
            <span>Legal placeholders only</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
