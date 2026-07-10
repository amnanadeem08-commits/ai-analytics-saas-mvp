import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://amnanadeem08-commits.github.io/ai-analytics-saas-mvp/sitemap.xml",
  };
}
