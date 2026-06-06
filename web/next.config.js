/** @type {import('next').NextConfig} */
const { PHASE_DEVELOPMENT_SERVER } = require('next/constants');

// Where the FastAPI backend is reachable during local development.
const DEV_API_TARGET = process.env.LIVERECALL_API_URL || 'http://localhost:8742';

module.exports = (phase) => {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;

  if (isDev) {
    // Dev server: run as a normal Node server (NOT static export) so we can
    // proxy API calls to the already-running FastAPI backend on :8742.
    return {
      images: { unoptimized: true },
      basePath: '',
      async rewrites() {
        return [
          {
            source: '/api/v1/:path*',
            destination: `${DEV_API_TARGET}/api/v1/:path*`,
          },
        ];
      },
    };
  }

  // Production build: static export for distribution (served by FastAPI itself).
  return {
    output: 'export',
    images: { unoptimized: true },
    basePath: '',
    trailingSlash: true,
  };
};
