# Dynamic Dashboard UX Audit

**Role:** Product Manager · UX Auditor · BI Consultant · First-Time Customer  
**Product:** Khaldoon AI — Dynamic Dashboard Builder (Sprint 10.0)  
**Date:** 2026-07-15  
**Scope:** Review only — **no implementation**  
**Method:** Code + interaction-path review of upload → Dashboard; templates, KPI resolver, visual rules, widget chrome, and page composition  

---

## Executive verdict

The engine correctly **assembles** domain-aware dashboards. A first-time customer will notice KPIs and charts appear after upload.  

They will **not** yet feel they stepped into a polished commercial BI canvas. The experience still reads as “Streamlit stacked sections with many control buttons,” with narrative duplication and weak domain visual identity beyond titles and metric labels.

**Score (first-session trust): 6.5 / 10** — functionally dynamic; emotionally and visually incomplete for a SaaS BI demo.

---

## Answers to the ten evaluation questions

| # | Question | Verdict |
|---|----------|---------|
| 1 | Feel dynamic after upload? | **Partially.** Charts/KPIs generate, but the “wow, it built *my* dashboard” moment is buried under page chrome (glossary, help, next-steps, filters, captions). |
| 2 | Business vs Healthcare vs Survey vs Mental Health visually obvious? | **Weak.** Titles and KPI names differ; same layout chrome, same chart styling, same button rows. Not a distinct product language per domain. |
| 3 | KPIs meaningful & domain-aware? | **Mostly when columns match.** Labels come from domain libraries; values are best-effort column matches and can look invented or weakly grounded when tokens miss. |
| 4 | Charts balanced vs random? | **Structure-aware, story-thin.** Rule priorities avoid empty slots, but intents can fill with generic bars; captions expose rule IDs (“Auto-selected via…”). |
| 5 | Story vs chart dump? | **Incomplete story.** Template order is right (summary → KPIs → visuals → AI → table), but sections don’t narrate “so what / now what” between visuals. |
| 6 | Executive Summary where expected? | **Present at top of template**, but often delayed by page intro, glossary, validation, tips, and widget chrome—then repeated again in a sidebar/insights block. |
| 7 | AI Insights add value or duplicate? | **Often duplicates.** Summary widget, AI Insights list, Recommendations, and page-level “Business Insights” retell similar lines. |
| 8 | Commercial BI vs Streamlit app? | **Still Streamlit-forward.** Per-widget Collapse/Refresh/Full buttons dominate; no dashboard “canvas,” sparse visual hierarchy. |
| 9 | Unnecessary clicks before value? | **Yes.** Users may expand Filters, scroll past help/glossary/next-steps, and interact with chrome before the KPI row feels primary. |
| 10 | Usability vs Power BI / Tableau / Looker Studio | **Principles lag.** Those tools give: (a) immediate canvas, (b) quiet chrome, (c) filters as ambient context, (d) one narrative page, (e) domain look via content density—not button bars. |

---

## Ranked UX issues

### Critical

#### C1 — Value delayed by pre-dashboard chrome
- **Root cause:** `render_dashboard` shows `page_intro`, Statistical Glossary expander, validation gate, domain KPI explainer, next-step buttons, and suggested-visuals caption *before* the dynamic dashboard canvas.
- **User impact:** First-time users wonder “Where is my dashboard?” and may leave before KPIs appear; the product feels like documentation, not analysis.
- **Recommended improvement:** Default path = Active Dataset ribbon + filters (collapsed) + Executive Summary + KPI row within the first viewport. Move glossary/help/next-steps behind an optional “Guide” affordance.
- **Effort:** S (0.5–1 day)

#### C2 — Widget chrome creates “tool UI” noise instead of a BI canvas
- **Root cause:** Every widget renders Collapse / Refresh / Full (and Export slot) as primary Streamlit buttons (`render_widget_chrome`), even when Export is unwired.
- **User impact:** Looks like a developer console; hides the visual story; feels nothing like Power BI/Tableau’s quiet hover actions.
- **Recommended improvement:** Collapse chrome to icon menus or hover-only; default view shows title + content only. Keep advanced controls behind “⋯”.
- **Effort:** M (1–2 days)

#### C3 — Domain difference is textual, not visual
- **Root cause:** Templates change section titles and KPI names, but renderer, chart theme, card chrome, and density are identical across Business / Healthcare / Survey / Mental Health.
- **User impact:** Customer uploading a clinical vs sales file gets the same “feel”; domain intelligence does not prove itself in a screenshot or demo video.
- **Recommended improvement:** Domain accent strips, section hero labels (“Clinical outcomes” vs “Revenue performance”), KPI iconography, and optional insight framing tone—still Khaldoon identity, not a BI clone.
- **Effort:** M–L (2–4 days)

---

### High

#### H1 — Narrative duplication (Summary + AI Insights + page Business Insights)
- **Root cause:** Engine builds `ai_panel`; template includes Executive Summary + AI Insights + Recommendations; page also renders a right-column Business Insights block and may restate `ai_panel`.
- **User impact:** Trust drops (“Same sentence three times”); AI feels padded rather than assistant-like.
- **Recommended improvement:** One narrative spine: Summary (top) → KPIs/charts → single “What this means / What to do” panel. Suppress page-level duplicate when dynamic spec is present.
- **Effort:** S–M (1 day)

#### H2 — KPI values can feel weakly grounded or misleading
- **Root cause:** `generate_domain_kpis` / smart KPI resolver matches column name tokens; when unmatched, cards may fall back to row counts or partial averages under a business label (e.g. “Growth” without a growth series).
- **User impact:** First-time customer distrusts the scorecard; domain awareness appears cosmetic.
- **Recommended improvement:** Show only grounded KPIs by default; mark ungrounded as “Recommended focus (no matching column)” secondary chips—not primary metrics. Prefer deltas/comparisons when time or segment available.
- **Effort:** M (1–2 days)

#### H3 — Chart captions expose engine internals
- **Root cause:** Materialized charts use subtitles like “Auto-selected via {rule_id}” and short insights that describe selection intent, not business meaning.
- **User impact:** Breaks the illusion of an analyst-built dashboard; sounds algorithmic/random.
- **Recommended improvement:** Business captions only (“Revenue concentrated in top regions”). Keep rule IDs in metadata/debug mode.
- **Effort:** S (0.5 day)

#### H4 — “Waterfall / Likert / Outcome” intents often render as ordinary bars
- **Root cause:** Chart materializer collapses many intents to standard bar/pie/line traces; survey/clinical distinctiveness is not visually specialized.
- **User impact:** Mental Health / Survey dashboards do not *look* different from Business beyond labels; promise of smart visuals under-delivers.
- **Recommended improvement:** Domain-special chart presets (ordered Likert axes, outcome stacked bars, contribution waterfall) when intent matches.
- **Effort:** M–L (2–3 days)

#### H5 — Local vs API paths feel inconsistent
- **Root cause:** Local Active Dataset uses engine directly; API path waits for backend `dynamic_dashboard` and still layers extra page chrome; classic view tucked in expander only on API success path.
- **User impact:** Demo offline vs online can look like two different products; confusion about what “dynamic” means.
- **Recommended improvement:** Single composition contract for both paths (same first viewport).
- **Effort:** M (1–2 days)

#### H6 — Filters are expandable “homework,” not ambient BI slicers
- **Root cause:** Filters live in an expander shared helper; not a persistent slicer strip aligned with KPIs.
- **User impact:** Power BI/Tableau users expect filters always in reach; here filtering feels optional and secondary.
- **Recommended improvement:** Compact horizontal filter chips above KPIs; active filters as removable tags; Reset visible without opening an expander.
- **Effort:** M (1–2 days)

---

### Medium

#### M1 — Executive Summary buried relatively, even when templated first
- **Root cause:** Template places summary first, but page preamble and per-widget button rows push visual KPIs down; summary styling is plain markdown, not a hero insight card.
- **User impact:** Users don’t “land” on the story; they land on controls.
- **Recommended improvement:** Treat Executive Summary as a distinct hero band (large type, 2–3 lines max, one CTA)—then KPIs.
- **Effort:** S (0.5–1 day)

#### M2 — Section headers are repetitive Streamlit `st.subheader`s
- **Root cause:** Renderer prints every template section title vertically with little visual rhythm or progressive disclosure.
- **User impact:** Long scroll of equally weighted blocks; tableau-like hierarchy missing.
- **Recommended improvement:** Stronger section hierarchy; collapse lower sections (Data Table, Saved dashboards) by default; sticky or tabbed “Overview | Analysis | Insights”.
- **Effort:** M (1–2 days)

#### M3 — Data Table at the bottom competes with analysis time
- **Root cause:** Templates always include a `data_table` section when rows exist.
- **User impact:** Commercial dashboards hide raw tables behind “View data”; first session over-emphasizes grids.
- **Recommended improvement:** Default collapsed “Underlying data”; show after insights.
- **Effort:** S (0.5 day)

#### M4 — Saved dashboard UI acknowledges incompleteness in product copy
- **Root cause:** Expander text: “Architecture ready… Sharing UI arrives in a later sprint.”
- **User impact:** Breaks customer immersion; feels unfinished SaaS.
- **Recommended improvement:** Either hide until ready or ship minimal Save/Open without roadmap language.
- **Effort:** S (0.25–0.5 day)

#### M5 — Dynamic hero identity is a dry caption
- **Root cause:** Renderer opens with `Template · Domain · Dataset` technical caption.
- **User impact:** Engineers like it; buyers don’t feel “Dashboard ready for Sales.”
- **Recommended improvement:** Human headline: “Sales performance for *filename* · Updated just now” with a quiet domain badge.
- **Effort:** S (0.5 day)

#### M6 — Classic dashboard expander duplicates density
- **Root cause:** API path offers “Classic dashboard view” with legacy KPIs/charts underneath dynamic layout.
- **User impact:** Choice paralysis; risk of comparing conflicting numbers.
- **Recommended improvement:** Hide classic behind Settings / debug for non-power users.
- **Effort:** S (0.25 day)

#### M7 — No “just uploaded → auto open Dashboard” triumphant moment
- **Root cause:** Upload completes on Upload page; user must navigate to Dashboard (even with Active Context).
- **User impact:** Extra click before value; power users of Looker Studio expect instant explore after connect.
- **Recommended improvement:** Post-upload primary CTA “Open your dashboard” that jumps with context already warm; optional auto-navigate for first dataset.
- **Effort:** S (0.5 day)

---

### Low

#### L1 — Statistical glossary on the Dashboard page
- **Root cause:** Educational expander always available on executive dashboard.
- **User impact:** Mild clutter; useful for students, wrong for executives as default.
- **Recommended improvement:** Move to Help / Learning center.
- **Effort:** S (0.25 day)

#### L2 — Empty Export buttons do nothing (when callback absent)
- **Root cause:** Chrome shows Export only if `on_export` provided, but Refresh always re-runs whole page; confusing semantics.
- **User impact:** Users click Refresh expecting widget reload; get full page reset.
- **Recommended improvement:** Label “Refresh dashboard”; wire per-widget export to Reports later.
- **Effort:** S (0.5 day)

#### L3 — Template metadata visible names (`grid_4` meaning unused)
- **Root cause:** `grid_4` layout with a single KPI widget still uses full-width path; naming promises denser KPI tiles than UX delivers relative to chrome.
- **User impact:** Minor—KPIs may feel sparse under button rows.
- **Recommended improvement:** KPI-only chrome (no Collapse/Full on metric rows).
- **Effort:** S (0.5 day)

#### L4 — Domain visual recommendations caption is list jargon
- **Root cause:** Page shows “Suggested visuals for domain: Line Charts · Bar Charts…” from profile strings.
- **User impact:** Redundant with actual charts; sounds like a checklist, not insight.
- **Recommended improvement:** Remove when dynamic dashboard is present.
- **Effort:** S (0.25 day)

---

## Comparative usability principles (not clones)

| Principle | Power BI / Tableau / Looker | Khaldoon Dynamic Dashboard today | Gap |
|-----------|-----------------------------|----------------------------------|-----|
| First viewport value | Canvas fills with scorecards | Help + chrome precede canvas | Large |
| Quiet interaction | Actions on hover / menu | Always-on button strip | Large |
| Filters ambient | Persistent slicers | Expander | Medium |
| Domain storytelling | Content density + titles | Titles + labels only | Medium–Large |
| One insight narrative | Summary/KPI focus | Multiple AI blocks | Medium |
| Progressive detail | Details optional | Table + classic + glossary | Medium |

**Usability takeaway:** Keep Khaldoon AI’s domain-aware narrative strength, but borrow *quiet chrome*, *first-viewport value*, and *one story spine*—without imitating Microsoft/Tableau skins.

---

## Priority roadmap (implementation guidance only)

1. **Critical bundle (demo-blocking):** C1 + C2 — clear first viewport + quiet chrome.  
2. **Trust bundle:** H1 + H2 + H3 — one story, grounded KPIs, human captions.  
3. **Differentiation bundle:** C3 + H4 — domains must be screenshot-obvious.  
4. **BI familiarity:** H6 + M1 + M3 — slicers, hero summary, hide raw table.  
5. **Polish:** M4–M7, L* as capacity allows.

---

## What already works (do not regress)

- Metadata-driven assembly (templates + rules) is the right architecture.  
- Empty chart placeholders are avoided.  
- Domain KPI libraries exist and General stays statistical.  
- Active Dataset context is respected.  
- Export path can consume dynamic charts.  
- Section *order* in templates matches BI storytelling intent.

---

## Audit conclusion

Sprint 10.0 delivers a credible **engine**. It does not yet deliver a credible **first-session BI experience**.  

The largest gap is not “more charts”—it is **presentation hierarchy**: fewer clicks, quieter chrome, one narrative, grounded KPIs, and domain-visible identity.

**Stop.** No changes implemented in this audit.
