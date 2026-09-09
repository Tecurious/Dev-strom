import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

// https://vite.dev/config/
export default defineConfig({
  // VITE_HTTPS=1 serves the dev server over a self-signed cert — needed for
  // Google OAuth, which refuses plain-http redirect URIs on non-localhost
  // hosts. Accept the browser's one-time cert warning.
  plugins: [react(), ...(process.env.VITE_HTTPS ? [basicSsl()] : [])],
  server: {
    // Dev server is reached over a private network (LAN / Tailscale MagicDNS),
    // so accept any Host header. Override with VITE_ALLOWED_HOSTS (comma list)
    // to lock it down.
    allowedHosts: process.env.VITE_ALLOWED_HOSTS
      ? process.env.VITE_ALLOWED_HOSTS.split(",").map((h) => h.trim())
      : true,
    // Behind the self-signed HTTPS host, point HMR's websocket at the same
    // origin so hot reload keeps working.
    hmr: process.env.VITE_HTTPS
      ? { protocol: "wss", clientPort: 5173 }
      : undefined,
    proxy: {
      // Forward /api/* to the local FastAPI backend during development.
      // The backend itself exposes routes at the root (e.g. /ideas, not
      // /api/ideas) — strip the /api prefix on the way through.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
