import Link from "next/link";
import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";
import { site } from "@/content/site";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-white/10">
      <div className="mx-auto grid max-w-site items-center gap-10 px-6 py-16 md:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] md:gap-12 md:py-24 lg:gap-16">
        <div className="max-w-xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">
            Business intelligence
          </p>
          <h1 className="mt-5 text-balance font-display text-[2.35rem] font-semibold leading-[1.08] tracking-tightest text-paper sm:text-5xl lg:text-[3.4rem]">
            Business intelligence,
            <span className="block text-paper/90">made practical.</span>
          </h1>
          <p className="mt-6 max-w-md text-base leading-relaxed text-muted sm:text-lg">
            {site.description}
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/#platform"
              className="inline-flex items-center rounded-md bg-amber px-5 py-2.5 text-sm font-medium text-ink transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
            >
              Explore Platform
            </Link>
            <Link
              href={site.links.booking}
              className="inline-flex items-center rounded-md border border-white/15 px-5 py-2.5 text-sm text-paper transition hover:border-white/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
            >
              Book a Demo
            </Link>
          </div>
          <p className="mt-6 max-w-sm text-sm text-muted">
            For CEOs, managers, analysts, and clients who need clear answers from real business data.
          </p>
        </div>

        <div className="min-w-0">
          <AnalyticsDashboard />
        </div>
      </div>
    </section>
  );
}
