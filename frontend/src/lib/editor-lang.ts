import type { Extension } from "@codemirror/state";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { sql } from "@codemirror/lang-sql";
import { yaml } from "@codemirror/lang-yaml";

export const languageMap = {
  js: () => javascript({ typescript: false, jsx: false }),
  ts: () => javascript({ typescript: true, jsx: false }),
  jsx: () => javascript({ typescript: false, jsx: true }),
  tsx: () => javascript({ typescript: true, jsx: true }),
  json: () => json(),
  yaml: () => yaml(),
  yml: () => yaml(),
  markdown: () => markdown(),
  md: () => markdown(),
  sql: () => sql(),
  python: () => python(),
  py: () => python(),
  java: () => java(),
  cpp: () => cpp(),
  c: () => cpp(),
  html: () => html(),
  css: () => css(),
  default: () => [],
};

export type LanguageType = keyof typeof languageMap;

export function getLanguageExtension(langKey: LanguageType): Extension[] {
  const key = langKey.toLowerCase() as LanguageType;
  const extensionFunc = languageMap[key] || languageMap["default"];

  return [extensionFunc()];
}
