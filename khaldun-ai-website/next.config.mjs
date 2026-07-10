/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
  // Required for GitHub project Pages: https://user.github.io/repo-name/
  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
