import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { ayonAddon } from "@ynput/ayon-addon-dev/vite";
import path from "path";

// ayonAddon() sets up module federation the way AYON loads addons: the remote "my_addon" (the
// key in frontend_modules, server/__init__.py) exposing ./manifest (src/manifest.ts), every
// package AYON provides shared, and @ynput/ayon-addon with import: false (always AYON's copy,
// never bundled). The build goes to dist/modules/my_addon.
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [react(), ayonAddon({ name: "my_addon" })],
});
