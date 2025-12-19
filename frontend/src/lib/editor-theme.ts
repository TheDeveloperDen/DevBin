import { EditorView } from "@codemirror/view";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags as t } from "@lezer/highlight";
import type { Extension } from "@codemirror/state";

const BACKGROUND = "#171717";
const FOREGROUND = "#e5e5e5";
const ACCENT_BLUE = "#005ff1";
const SUBTLE_GREY = "#3a3a3a";
const SELECTION = "#a1a1a1";

const KEYWORD = "#ff52f9";
const COMMENT = "#00afc3";
const STRING = "#8099ff";
const NUMBER = ACCENT_BLUE;
const PROPERTY = "#00afc3";

const highlightStyle = HighlightStyle.define([
  { tag: t.keyword, color: KEYWORD, fontWeight: "bold" },
  { tag: t.comment, color: COMMENT, fontStyle: "italic" },
  { tag: t.string, color: STRING },
  { tag: t.number, color: NUMBER },
  { tag: t.propertyName, color: PROPERTY },
  { tag: t.operator, color: KEYWORD },
  { tag: t.variableName, color: FOREGROUND },
  { tag: t.name, color: FOREGROUND },
]);

const theme = EditorView.theme(
  {
    "&": {
      color: FOREGROUND,
      backgroundColor: BACKGROUND,

      fontFamily: '"Cascadia Code", sans-serif',
      border: `1px solid ${SUBTLE_GREY}`,
      borderRadius: "0.5rem",
      height: "100%",
      minHeight: "400px",
      fontSize: "0.875rem",
    },

    ".cm-gutters": {
      backgroundColor: BACKGROUND,
      color: SUBTLE_GREY,
      borderRight: "none",
      paddingRight: "8px",
    },

    ".cm-content": {
      caretColor: ACCENT_BLUE,
    },
    ".cm-cursor, .cm-dropCursor": {
      borderLeftColor: ACCENT_BLUE,
    },

    ".cm-selectionBackground": {
      backgroundColor: SELECTION,
    },

    ".cm-activeLine": {
      backgroundColor: "transparent",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "transparent",
      color: SELECTION,
    },

    ".cm-placeholder": {
      color: SUBTLE_GREY,
    },
  },
  { dark: true },
);

export const editorTheme: Extension[] = [
  theme,
  syntaxHighlighting(highlightStyle),
];
