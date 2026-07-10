export type ProductStatus = "available" | "signal-only" | "coming-next";

export type Product = {
  id: string;
  code: string;
  name: string;
  tagline: string;
  description: string;
  href: string;
  status: ProductStatus;
  statusLabel: string;
};

export type SiteLink = {
  label: string;
  href: string;
  external?: boolean;
};

export const site = {
  name: "Khaldun AI",
  tagline: "Find the pattern. Ship the dashboard.",
  description:
    "We turn messy business data into clear KPIs, automated Excel workflows, practical CRM tools, and careful market signals — for teams that need results, not slogans.",
  email: "hello@khaldun.ai",
  links: {
    fiverr: "https://www.fiverr.com/", // TODO: replace with real profile URL
    upwork: "https://www.upwork.com/", // TODO: replace with real profile URL
    linkedin: "https://www.linkedin.com/", // TODO: replace with real profile URL
  } as Record<string, string>,
};

export const nav: SiteLink[] = [
  { label: "Products", href: "/#products" },
  { label: "How we work", href: "/#how-we-work" },
  { label: "Proof", href: "/#proof" },
  { label: "Contact", href: "/#contact" },
];

export const products: Product[] = [
  {
    id: "data",
    code: "01",
    name: "Khaldun Data",
    tagline: "AI data analytics platform",
    description:
      "KPI engine, DAX-style calculations, SQL copilot, natural-language charts and reports, plus PDF / PPTX / Excel export.",
    href: "/products/data/",
    status: "available",
    statusLabel: "AVAILABLE",
  },
  {
    id: "excel",
    code: "02",
    name: "Khaldun Excel",
    tagline: "Excel automation for business teams",
    description:
      "No-code Excel automation and dashboard builder for teams that live in spreadsheets (formerly ExcelMVP).",
    href: "/products/excel/",
    status: "available",
    statusLabel: "AVAILABLE",
  },
  {
    id: "crm",
    code: "03",
    name: "Khaldun CRM",
    tagline: "CRM for local and small businesses",
    description:
      "A lightweight CRM built for local and small businesses that need follow-ups without enterprise overhead (formerly Smart CRM).",
    href: "/products/crm/",
    status: "available",
    statusLabel: "AVAILABLE",
  },
  {
    id: "trade",
    code: "04",
    name: "Khaldun Trade",
    tagline: "Market signal generation",
    description:
      "LLM-assisted signals across Binance crypto and PSX, combining RSI / MACD / candlestick reads with Fear & Greed sentiment. Signal-only / paper trading — not live execution or profit guarantees.",
    href: "/products/trade/",
    status: "signal-only",
    statusLabel: "SIGNAL-ONLY / PAPER",
  },
];

export const futureProducts: Product[] = [
  {
    id: "vision",
    code: "05",
    name: "Khaldun Vision",
    tagline: "Computer vision",
    description: "Computer vision capabilities — not built yet.",
    href: "/#products",
    status: "coming-next",
    statusLabel: "COMING NEXT",
  },
];

export const howWeWork = {
  title: "How we work",
  lead: "Two ways in — same team.",
  items: [
    {
      title: "Project work",
      body: "Hire us on Fiverr, Upwork, or LinkedIn for dashboards, Excel automation, and data cleanup. You get a scoped deliverable and a clear handoff.",
    },
    {
      title: "Product trials",
      body: "Try Khaldun Data when you want a reusable analytics platform instead of a one-off file. Start small, keep what works.",
    },
  ],
};

export const proof = {
  title: "Proof",
  note: "TODO: replace with real content — case studies, client logos, or anonymized before/after metrics. Do not invent testimonials.",
  placeholders: [
    { label: "Case study slot A", detail: "TODO: real engagement summary" },
    { label: "Case study slot B", detail: "TODO: real engagement summary" },
    { label: "Logo / reference slot", detail: "TODO: permissioned client mark" },
  ],
};

export const contact = {
  title: "Tell us what the data should answer",
  body: "Send the problem in plain language — spreadsheet chaos, KPI definitions, CRM follow-ups, or signal research. We will reply with a practical next step.",
  ctaLabel: "Email Khaldun AI",
  mailto: "mailto:hello@khaldun.ai?subject=Project%20inquiry%20%E2%80%94%20Khaldun%20AI",
};
