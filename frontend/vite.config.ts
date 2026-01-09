import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import { rollupWasm } from "@ethercorps/sveltekit-og/plugin";
import { sveltekitOG } from "@ethercorps/sveltekit-og/plugin";

export default defineConfig({
  server: {
    port: parseInt(process.env.PORT || "3000"),
    allowedHosts: [
      "73e9cd75c0f1.ngrok-free.app",
      "sustainability-odds-undo-knows.trycloudflare.com",
    ],
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
