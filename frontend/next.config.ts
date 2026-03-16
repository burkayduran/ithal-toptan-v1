import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // Placeholder / demo images
      { protocol: "https", hostname: "images.unsplash.com" },
      // Common image CDNs and storage providers used by the backend
      { protocol: "https", hostname: "*.cloudflare.com" },
      { protocol: "https", hostname: "*.cloudinary.com" },
      { protocol: "https", hostname: "*.supabase.co" },
      { protocol: "https", hostname: "*.supabase.in" },
      { protocol: "https", hostname: "*.amazonaws.com" },
      { protocol: "https", hostname: "*.r2.dev" },
      // Add your own bucket/CDN hostname here when known, e.g.:
      // { protocol: "https", hostname: "cdn.ithal-toptan.com" },
    ],
  },
};

export default nextConfig;
