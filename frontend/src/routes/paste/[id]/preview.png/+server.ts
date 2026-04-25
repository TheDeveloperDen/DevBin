import type { RequestHandler } from "@sveltejs/kit";
import { ApiService } from "$lib/api";
import type { Paste } from "$lib/types";
import { env } from "$env/dynamic/private";
import { getUserIpAddress } from "$lib/utils/ip";
import { createHighlighter, type Highlighter } from "shiki";
import { languageMap } from "$lib/editor-lang";
import sharp from "sharp";
import { readFileSync } from "fs";
import { resolve } from "path";

const SCALE = 2;
const WIDTH = 1200;
const HEIGHT = 630;
const BG = "#0d1117";
const HEADER_H = 70;
const FONT_SIZE = 13;
const LINE_HEIGHT = 20;
const CHAR_WIDTH = FONT_SIZE * 0.601;
const GUTTER_W = 52;
const CODE_X = GUTTER_W + 12;
const CODE_Y = HEADER_H + FONT_SIZE + 8;
const FADE_H = 10;
const MAX_LINES = Math.floor((HEIGHT - CODE_Y - FADE_H) / LINE_HEIGHT);
const FONT = "Cascadia Code";
const THEME = "ayu-dark";

let highlighter: Highlighter;

async function getHighlighter() {
  if (!highlighter) {
    highlighter = await createHighlighter({
      themes: [THEME],
      langs: Object.keys(languageMap).filter((l) => l !== "plain_text"),
    });
  }
  return highlighter;
}

function expandTabs(str: string, size = 2) {
  return str.replace(/\t/g, " ".repeat(size));
}

function escapeXml(str: string) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function loadFontBase64(path: string): string | null {
  try {
    return readFileSync(resolve("static", path)).toString("base64");
  } catch {
    return null;
  }
}

function buildSvg(
  title: string,
  language: string,
  tokens: ReturnType<Highlighter["codeToTokens"]>,
) {
  const fg = tokens.fg ?? "#e6edf3";
  const fontBase64 = loadFontBase64("fonts/CascadiaCode-VariableFont_wght.ttf");
  const filename = escapeXml(
    `${title}.${language}`,
  );

  let codeRows = "";
  tokens.tokens.forEach((lineTokens, i) => {
    const y = CODE_Y + i * LINE_HEIGHT;
    let x = CODE_X;
    let tspans = "";

    codeRows += `<text x="${GUTTER_W}" y="${y}" fill="#484f58" font-family="${FONT},monospace" font-size="${FONT_SIZE}" text-anchor="end">${i + 1}</text>`;

    for (const token of lineTokens) {
      const text = expandTabs(token.content);
      tspans += `<tspan x="${x}" fill="${token.color ?? fg}">${escapeXml(text)}</tspan>`;
      x += text.length * CHAR_WIDTH;
    }

    if (tspans) {
      codeRows += `<text y="${y}" font-family="${FONT},monospace" font-size="${FONT_SIZE}" xml:space="preserve">${tspans}</text>`;
    }
  });
  
  return `<svg width="${WIDTH * SCALE}" height="${HEIGHT * SCALE}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    ${fontBase64 ? `<style>@font-face { font-family: "${FONT}"; src: url("data:font/truetype;base64,${fontBase64}") format("truetype"); }</style>` : ""}
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${BG}" stop-opacity="0"/>
      <stop offset="100%" stop-color="${BG}" stop-opacity="1"/>
    </linearGradient>
  </defs>

  <rect width="${WIDTH}" height="${HEIGHT}" fill="${BG}"/>
  <rect width="${WIDTH}" height="${HEADER_H}" fill="#161b22"/>

  <text x="${WIDTH / 2}" y="${HEADER_H / 2 + 5}" fill="#8b949e" font-family="${FONT},monospace" font-size="13" text-anchor="middle">${filename}</text>

  <line x1="0" y1="${HEADER_H}" x2="${WIDTH}" y2="${HEADER_H}" stroke="#30363d" stroke-width="1"/>
  <line x1="${GUTTER_W + 6}" y1="${HEADER_H}" x2="${GUTTER_W + 6}" y2="${HEIGHT}" stroke="#21262d" stroke-width="1"/>

  ${codeRows}

  <rect x="0" y="${HEIGHT - 110}" width="${WIDTH}" height="${110}" fill="url(#fade)"/>
</svg>`;
}

export const GET: RequestHandler = async ({
  params,
  request,
  getClientAddress,
}) => {
  const { id } = params;
  const clientIp = getUserIpAddress(request, getClientAddress);

  let title = "DevBin";
  let content = "// no content";
  let language = "yaml";

  if (id) {
    const { data } = await ApiService.getPasteByUuidPastesPasteIdGet({
      baseUrl: env.API_URL,
      path: { paste_id: id },
      headers: { "X-Forwarded-For": clientIp },
    });
    if (data) {
      const paste = data as Paste;
      title = paste.title || "DevBin";
      content = paste.content;
      language = paste.content_language;
    }
  }

  const h = await getHighlighter();
  const lang = h.getLoadedLanguages().includes(language as any)
    ? (language as any)
    : "text";

  const allLines = content.split("\n").map(expandTabs);
  const lines =
    allLines.length <= MAX_LINES ? allLines : allLines.slice(0, MAX_LINES);
  const tokens = h.codeToTokens(lines.join("\n"), { lang, theme: THEME });
  const svg = buildSvg(title, language, tokens);

  const png = await sharp(Buffer.from(svg))
    .resize(WIDTH, HEIGHT, { kernel: sharp.kernel.lanczos3 })
    .png({ compressionLevel: 9 })
    .toBuffer();

  return new Response(png, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=3600",
    },
  });
};
