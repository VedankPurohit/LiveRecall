/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API requests to FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8742/api/:path*',
      },
    ];
  },
  // Allow images from local filesystem
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8742',
      },
    ],
    unoptimized: true,
  },
};

module.exports = nextConfig;
