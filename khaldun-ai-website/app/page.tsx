import { site } from "@/content/site";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-site flex-col justify-center px-6 py-24">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">
        phase 1 · tokens online
      </p>
      <h1 className="mt-4 font-display text-4xl font-semibold tracking-tightest text-paper md:text-6xl">
        {site.name}
      </h1>
      <p className="mt-4 max-w-xl text-lg text-muted">{site.tagline}</p>
      <div className="mt-10 grid gap-3 font-mono text-sm text-paper/80 sm:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-panel p-4">
          <div className="text-muted">ink</div>
          <div>#0B0F19</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-panel p-4">
          <div className="text-signal">signal</div>
          <div>#17D9C4</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-panel p-4">
          <div className="text-amber">amber</div>
          <div>#F2A93B</div>
        </div>
      </div>
    </main>
  );
}
