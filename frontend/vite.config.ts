import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import { rollupWasm } from "@ethercorps/sveltekit-og/plugin";
import { sveltekitOG } from "@ethercorps/sveltekit-og/plugin";

export default defineConfig({
  server: {
    port: process.env.PORT || 3000,
  },
  build: {
    rollupOptions: {
      plugins: [rollupWasm()],
    },
  },
  plugins: [tailwindcss(), sveltekit(), sveltekitOG()],
  optimizeDeps: {
    exclude: [
      "svelte-codemirror-editor",
      "codemirror",
      "@codemirror/language-javascript",
    ],
  },
});
