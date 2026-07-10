export type ProductStatus = "ready" | "coming-soon" | "labs";

export type Product = {
  id: string;
  name: string;
  value: string;
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
  tagline: "Business intelligence, made practical.",
  description:
    "Turn Excel, CSV, and SQL data into dashboards, AI insights, executive reports, and clearer decisions.",
  email: "hello@khaldun.ai",
  businessHours: "Mon–Fri · 10:00–19:00 PKT (Asia/Karachi)",
  links: {
    fiverr: "https://www.fiverr.com/", // TODO: replace with real profile URL
    upwork: "https://www.upwork.com/", // TODO: replace with real profile URL
    linkedin: "https://www.linkedin.com/", // TODO: replace with real profile URL
    github: "https://github.com/amnanadeem08-commits/ai-analytics-saas-mvp",
    booking: "mailto:hello@khaldun.ai?subject=Demo%20request%20%E2%80%94%20Khaldun%20AI",
  } as Record<string, string>,
};

export const nav: SiteLink[] = [
  { label: "Products", href: "/#products" },
  { label: "Platform", href: "/#platform" },
  { label: "Services", href: "/#services" },
  { label: "Engineering", href: "/#engineering" },
  { label: "Contact", href: "/#contact" },
];

export const products: Product[] = [
  {
    id: "data",
    name: "AI Data Bot",
    value: "Upload business data. Receive dashboards and AI insights.",
    href: "/products/data/",
    status: "ready",
    statusLabel: "READY",
  },
  {
    id: "excel",
    name: "ExcelMVP",
    value: "Create professional dashboards inside Excel.",
    href: "/products/excel/",
    status: "ready",
    statusLabel: "READY",
  },
  {
    id: "crm",
    name: "Smart CRM",
    value: "Simple CRM for growing businesses.",
    href: "/products/crm/",
    status: "coming-soon",
    statusLabel: "COMING SOON",
  },
  {
    id: "labs",
    name: "Khaldun Labs",
    value:
      "Research lab for machine learning, forecasting, business intelligence, AI experiments, and quantitative research.",
    href: "/products/labs/",
    status: "labs",
    statusLabel: "LABS",
  },
];

export const engineeringMetrics = [
  { value: 633, suffix: "+", label: "Automated tests" },
  { value: 40, suffix: "+", label: "Core modules" },
];

export const engineeringCapabilities = [
  "AI workflow engine",
  "Multi-agent AI",
  "RAG knowledge retrieval",
  "Evaluation framework",
  "FastAPI backend",
  "Streamlit workspace",
  "Python analytics stack",
  "Role-based security",
  "Storage versioning",
  "Background workers",
  "REST APIs",
  "Production monitoring",
];

export const platformScreens = [
  {
    id: "dashboard",
    title: "Dashboard",
    caption: "KPI cards, trends, and segment views from uploaded data.",
  },
  {
    id: "report",
    title: "Executive report",
    caption: "Board-ready narrative with export to PDF and PowerPoint.",
  },
  {
    id: "analyst",
    title: "AI Analyst",
    caption: "Ask questions in plain language; get grounded answers.",
  },
  {
    id: "upload",
    title: "Data upload",
    caption: "CSV and Excel in, cleaned tables and schema out.",
  },
  {
    id: "workflow",
    title: "Workflow",
    caption: "Step-by-step analysis pipeline with clear status.",
  },
  {
    id: "knowledge",
    title: "Knowledge Center",
    caption: "Ingest documents so answers stay close to your business context.",
  },
  {
    id: "evaluation",
    title: "Evaluation",
    caption: "Score insight quality before you present it.",
  },
  {
    id: "storage",
    title: "Storage",
    caption: "Versioned artifacts with download and rollback.",
  },
];

export const milestones = {
  dataBot: {
    title: "AI Data Bot v1.0",
    items: [
      "633+ automated tests",
      "Production API",
      "Workflow engine",
      "Evaluation framework",
      "Authentication",
      "RBAC",
      "Storage",
      "Background jobs",
    ],
  },
  excel: {
    title: "ExcelMVP",
    items: ["Dashboard builder", "Export engine", "Visualization"],
  },
  coming: {
    title: "Coming soon",
    items: ["Smart CRM", "Client case studies by industry"],
  },
};

export const industries = ["Healthcare", "Sales", "Finance", "Manufacturing"];

export const services = [
  {
    title: "Business Intelligence",
    body: "Define KPIs, build reporting models, and keep leadership aligned on one source of truth.",
  },
  {
    title: "Power BI development",
    body: "Measures, models, and report canvases that match how your team already works.",
  },
  {
    title: "Excel automation",
    body: "Replace manual spreadsheet routines with repeatable dashboard and export flows.",
  },
  {
    title: "Dashboard development",
    body: "Clear visuals for operators and executives — not chart clutter.",
  },
  {
    title: "Data analytics",
    body: "Explore patterns in sales, operations, and finance data with practical next steps.",
  },
  {
    title: "AI reporting",
    body: "Natural-language summaries and insight drafts grounded in your tables.",
  },
  {
    title: "Python automation",
    body: "Scripts and services for cleaning, joining, and refreshing recurring datasets.",
  },
  {
    title: "SQL analytics",
    body: "Query design and SQL-assisted exploration for teams with warehouse access.",
  },
  {
    title: "Forecasting",
    body: "Trend and scenario views when you need a careful look at what may come next.",
  },
];

export const whySteps = [
  { title: "Business problem", detail: "What decision is blocked?" },
  { title: "Upload data", detail: "Excel, CSV, or SQL-ready tables" },
  { title: "AI processing", detail: "Clean, profile, analyze" },
  { title: "Dashboard", detail: "KPIs and visuals you can trust" },
  { title: "Insights", detail: "Plain-language findings" },
  { title: "Decision", detail: "Act with clearer evidence" },
];

export const faq = [
  {
    q: "Do you only sell software?",
    a: "No. We deliver project work (dashboards, Excel, BI) and product platforms. Many clients start with a scoped project.",
  },
  {
    q: "Is AI Data Bot ready to use?",
    a: "Yes — v1.0 is released with a production API, auth, workflows, storage, and a large automated test suite.",
  },
  {
    q: "Do you invent client results?",
    a: "No. We do not publish fake testimonials or fake user counts. Case studies appear only when we have permission.",
  },
];

export const contact = {
  title: "Tell us the decision you need to make",
  body: "Describe the data you have and the question leadership keeps asking. We will reply with a practical next step — project scope or platform walkthrough.",
  ctaLabel: "Email Khaldun AI",
  demoLabel: "Book a demo",
  mailto: "mailto:hello@khaldun.ai?subject=Project%20inquiry%20%E2%80%94%20Khaldun%20AI",
};

export const howWeWork = {
  title: "How we work",
  lead: "Freelance delivery and product platforms — same standards.",
  items: [
    {
      title: "Project delivery",
      body: "Hire us for Power BI, Excel, dashboards, and data cleanup. Scoped work, clear handoff.",
    },
    {
      title: "Platform access",
      body: "Use AI Data Bot when you want a reusable analytics workspace instead of a one-off file.",
    },
  ],
};
