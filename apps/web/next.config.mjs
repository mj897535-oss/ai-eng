/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async redirects() {
    return [
      {
        source: '/pre-test',
        destination: '/assessment/pre',
        permanent: true,
      },
      {
        source: '/post-test',
        destination: '/assessment/post',
        permanent: true,
      },
      {
        source: '/student/assessment',
        destination: '/assessment/pre',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
