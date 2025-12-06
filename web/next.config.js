/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable static export for distribution
  output: 'export',

  // Disable image optimization (not available in static export)
  images: {
    unoptimized: true,
  },

  // Base path for assets (empty for root)
  basePath: '',

  // Trailing slashes for static file serving
  trailingSlash: true,
};

module.exports = nextConfig;
