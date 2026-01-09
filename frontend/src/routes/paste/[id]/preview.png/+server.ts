import type { RequestHandler } from "@sveltejs/kit";
import { ApiService } from "$lib/api";
import type { Paste } from "$lib/types";
import { env } from "$env/dynamic/private";
import { getUserIpAddress } from "$lib/utils/ip";
import { createHighlighter, type Highlighter } from "shiki";
import sharp from "sharp";

let highlighter: Highlighter;

async function getHighlighter() {
  if (!highlighter) {
    highlighter = await createHighlighter({
      themes: ["github-dark"],
      langs: ["yaml", "typescript", "javascript", "python", "json"],
    });
  }
  return highlighter;
}

export const GET: RequestHandler = async ({
  params,
  request,
  getClientAddress,
}) => {
  const client_ip = getUserIpAddress(request, getClientAddress);
  const { id } = params;
  let title = "DevBin";
  let content = "";
  let content_language = "yaml";

  // 1. Fetch Paste Data
  if (id) {
    const response = await ApiService.getPasteByUuidPastesPasteIdGet({
      baseUrl: env.API_URL,
      path: { paste_id: id },
      headers: { "X-Forwarded-For": client_ip },
    });
    if (response.data) {
      const data = response.data as Paste;
      title = data.title || "DevBin";
      content = data.content;
      content_language = data.content_language;
    }
  }

  const h = await getHighlighter();
  // Increase line count slightly to match the editor screenshot density
  const linesToRender = content.split("\n").slice(0, 22);
  const tokenResult = h.codeToTokens(linesToRender.join("\n"), {
    lang: "yaml",
    theme: "github-dark",
  });

  const defaultColor = tokenResult.fg || "#e6edf3";
  const lineHeight = 26;
  const charWidth = 9.6; // Calculated for 16px monospace
  const startY = 110;
  const codeStartX = 75;

  let codeLinesSvg = "";
  tokenResult.tokens.forEach((line, i) => {
    const y = startY + i * lineHeight;

    // Active Line Highlight (matching line 16 in your screenshot)
    if (i + 1 === 16) {
      codeLinesSvg += `<rect x="0" y="${y - 19}" width="1200" height="${lineHeight}" fill="#21262d" opacity="0.4" />`;
    }

    // Line Number
    codeLinesSvg += `<text x="35" y="${y}" fill="#484f58" font-family="monospace" font-size="14" text-anchor="end">${i + 1}</text>`;

    // Block Folding Icon (v)
    const lineStr = line.map((t) => t.content).join("");
    if (lineStr.trim().endsWith(":")) {
      codeLinesSvg += `<text x="48" y="${y - 1}" fill="#484f58" font-family="monospace" font-size="12">v</text>`;
    }

    // Code Content with precise spacing
    let currentX = codeStartX;
    line.forEach((token) => {
      const escaped = token.content
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      codeLinesSvg += `<text x="${currentX}" y="${y}" fill="${token.color || defaultColor}" font-family="monospace" font-size="16" xml:space="preserve">${escaped}</text>`;

      // Advance X based on character count to fix tab/space issues
      currentX += token.content.length * charWidth;
    });
  });

  const svgTemplate = `
    <svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
        <rect width="1200" height="630" fill="#0d1117" />

        <text x="600" y="40" fill="#e6edf3" font-family="sans-serif" font-weight="600" font-size="18" text-anchor="middle">${title}</text>
        <line x1="0" y1="70" x2="1200" y2="70" stroke="#30363d" stroke-width="1" />

        ${codeLinesSvg}

        <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0d1117" stop-opacity="0" />
            <stop offset="100%" stop-color="#0d1117" stop-opacity="1" />
        </linearGradient>
        <rect x="0" y="520" width="1200" height="110" fill="url(#fade)" />
    </svg>`;

  const pngBuffer = await sharp(Buffer.from(svgTemplate)).png().toBuffer();

  return new Response(pngBuffer, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=3600",
    },
  });
};
