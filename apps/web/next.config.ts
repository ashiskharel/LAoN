import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.metmuseum.org" },
      { protocol: "https", hostname: "openaccess-cdn.clevelandart.org" },
      { protocol: "https", hostname: "**.clevelandart.org" },
      { protocol: "https", hostname: "**.metmuseum.org" },
    ],
  },
};

export default nextConfig;
