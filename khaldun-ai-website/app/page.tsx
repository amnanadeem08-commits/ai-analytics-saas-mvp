import { Hero } from "@/components/Hero";
import { SiteHeader } from "@/components/SiteHeader";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <div className="mx-auto max-w-site px-6 py-16">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
            phase 2 · hero instrument online — remaining sections next
          </p>
        </div>
      </main>
    </>
  );
}
