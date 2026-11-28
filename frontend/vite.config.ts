import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API CORS ayari localhost:5173'e izin veriyor; port sabit kalsin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
