# Khaldun AI Website

Marketing site for **Khaldun AI** — an AI-powered data analytics company.

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS
- Framer Motion
- Static export (`output: "export"`)

## Develop

```bash
npm install
npm run dev
```

## Build static site

```bash
npm run build
```

Output lands in `out/`.

### GitHub Pages

On push to `main` (when this folder changes), GitHub Actions builds and deploys the site.

**Public URL (after Pages is enabled):**  
https://amnanadeem08-commits.github.io/ai-analytics-saas-mvp/

Local `npm run dev` stays at http://localhost:3000 (no base path).

## Content

Edit typed content in `content/site.ts`.
