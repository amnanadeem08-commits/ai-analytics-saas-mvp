import type { MetadataRoute } from "next";

const base = "https://amnanadeem08-commits.github.io/ai-analytics-saas-mvp";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${base}/`, lastModified: new Date(), changeFrequency: "weekly", priority: 1 },
    { url: `${base}/products/data/`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/products/excel/`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/products/crm/`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/products/labs/`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
  ];
}
