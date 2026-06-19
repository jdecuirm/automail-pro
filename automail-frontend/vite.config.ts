/// <reference types="vitest/config" />
import path from "path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (
            id.includes("/node_modules/react/") ||
            id.includes("/node_modules/react-dom/") ||
            id.includes("/node_modules/react-router")
          ) {
            return "vendor-react";
          }
          if (
            id.includes("/node_modules/radix-ui/") ||
            id.includes("/node_modules/cmdk/") ||
            id.includes("/node_modules/lucide-react/") ||
            id.includes("/node_modules/class-variance-authority/") ||
            id.includes("/node_modules/clsx/") ||
            id.includes("/node_modules/tailwind-merge/") ||
            id.includes("/node_modules/sonner/")
          ) {
            return "vendor-ui";
          }
          if (
            id.includes("/node_modules/@tanstack/") ||
            id.includes("/node_modules/zod/") ||
            id.includes("/node_modules/react-hook-form/") ||
            id.includes("/node_modules/@hookform/")
          ) {
            return "vendor-data";
          }
          if (id.includes("/node_modules/recharts/")) {
            return "vendor-charts";
          }
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
