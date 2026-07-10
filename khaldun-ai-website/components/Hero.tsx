import Link from "next/link";
import { DataInstrument } from "@/components/DataInstrument";
import { site } from "@/content/site";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-white/10">
      <div className="mx-auto grid max-w-site gap-10 px-6 py-14 sm:py-16 md:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] md:items-center md:gap-12 md:py-24 lg:gap-16">
        <div className="order-1 md:order-1">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">
            Khaldun AI · data company
          </p>
          <h1 className="mt-5 max-w-xl text-balance font-display text-[2rem] font-semibold leading-[1.1] tracking-tightest text-paper sm:text-5xl lg:text-6xl">
            Patterns in your data, ready for decisions
          </h1>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-muted sm:text-lg">
            {site.description}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3 sm:gap-4">
            <Link
              href="/#products"
              className="inline-flex items-center rounded-md bg-amber px-5 py-2.5 text-sm font-medium text-ink transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
            >
              See the platform
            </Link>
            <Link
              href="/#contact"
              className="inline-flex items-center rounded-md border border-white/15 px-5 py-2.5 text-sm text-paper transition hover:border-white/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
            >
              Talk to us
            </Link>
          </div>
          <p className="mt-6 font-mono text-[11px] text-muted">
            From Excel cleanup to KPI systems — honest scope, shipped work.
          </p>
        </div>

        <div className="order-2 min-w-0 md:order-2">
          <DataInstrument className="w-full max-w-full" />
        </div>
      </div>
    </section>
  );
}
