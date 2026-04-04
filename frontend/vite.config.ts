import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import { rollupWasm } from "@ethercorps/sveltekit-og/plugin";
import { sveltekitOG } from "@ethercorps/sveltekit-og/plugin";

console.log(process.env.ALLOWED_HOSTS);
export default defineConfig({
  server: {
    port: parseInt(process.env.PORT || "3000"),
    allowedHosts: [
      "techno-blink-fields-details.trycloudflare.com"
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
