import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发态代理到本机 FastAPI（T02/T03）；浏览器只访问同源路径，由 Vite 转发。
// 后端默认：127.0.0.1:8787（见 backend README）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/notion": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
      },
    },
  },
});
