import type { NextConfig } from "next";

const staticConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  }
};

const ssrConfig: NextConfig = {};

export default (process.env.NEXT_BUILD_CONFIG === 'static' ? staticConfig : ssrConfig);
