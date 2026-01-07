import { EditorView } from "@codemirror/view";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags as t } from "@lezer/highlight";

export const customHighlight = HighlightStyle.define([
  { tag: t.keyword, color: "#c084fc", fontWeight: "bold" },
  { tag: t.self, color: "#f87171" },
  { tag: t.modifier, color: "#c084fc" },

  { tag: t.function(t.variableName), color: "#38bdf8" },
  {
    tag: t.definition(t.function(t.variableName)),
    color: "#7dd3fc",
    fontWeight: "bold",
  },
  { tag: t.className, color: "#fbbf24" },
  { tag: t.macroName, color: "#f472b6" },

  { tag: t.variableName, color: "#e5e7eb" },
  { tag: t.propertyName, color: "#818cf8" },
  { tag: t.namespace, color: "#a78bfa" },

  { tag: t.string, color: "#4ade80" },
  { tag: t.docString, color: "#4ade80", fontStyle: "italic" },
  { tag: t.number, color: "#fbbf24" },
  { tag: t.bool, color: "#fbbf24" },
  { tag: t.null, color: "#fbbf24" },

  { tag: t.operator, color: "#22d3ee" },
  { tag: t.punctuation, color: "#9ca3af" },
  { tag: t.bracket, color: "#9ca3af" },

  { tag: t.comment, color: "#6b7280", fontStyle: "italic" },
]);

export const customTheme = EditorView.theme(
  {
    "&": {
      color: "#e0e0e0",
      backgroundColor: "#121212",
    },
    ".cm-content": {
      caretColor: "#fff",
      fontFamily: "Cascadia Code",
    },
    ".cm-cursor, .cm-dropCursor": { borderLeftColor: "#fff" },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection":
      {
        backgroundColor: "rgba(128, 153, 255, 0.2) !important",
      },
    ".cm-gutters": {
      backgroundColor: "#121212",
      color: "#4b5563",
      border: "none",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "#1e1e1e",
      color: "#e0e0e0",
    },
    ".cm-activeLine": {
      backgroundColor: "rgba(128, 153, 255, 0.1)",
    },
  },
  { dark: true },
);
