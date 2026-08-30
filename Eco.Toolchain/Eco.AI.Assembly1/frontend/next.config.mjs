/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: `next build` emits a fully static site into ./out which is
  // shipped inside the wheel (eco_harness/web_static) and served by FastAPI on
  // the same port — no Node.js on customer machines. The dev stack (docker
  // compose) still runs `next dev` and is unaffected.
  output: "export",
  // Folder-browser pages read the path from the query string client-side;
  // static export cannot use server middleware/rewrites.
  trailingSlash: false,
  images: { unoptimized: true },
};

export default nextConfig;
