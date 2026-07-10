import Link from "next/link";
import { nav, site } from "@/content/site";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/90 backdrop-blur">
      <div className="mx-auto flex max-w-site items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="font-display text-lg font-semibold tracking-tight text-paper">
          {site.name}
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-6 text-sm text-muted md:flex">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} className="transition hover:text-paper">
              {item.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/#contact"
          className="rounded-md border border-white/15 px-3 py-1.5 text-xs font-medium text-paper transition hover:border-amber/60 hover:text-amber md:text-sm"
        >
          Contact
        </Link>
      </div>
    </header>
  );
}
