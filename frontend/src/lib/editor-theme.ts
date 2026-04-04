import { EditorView } from "@codemirror/view";

export function customTheme(bg: string = "#121212") {
  return EditorView.theme(
    {
      "&": {
        color: "#e0e0e0",
        backgroundColor: bg,
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
        backgroundColor: bg,
        color: "#4b5563",
        border: "none",
      },
      ".cm-activeLineGutter": {
        backgroundColor: bg + "cc", // dim bg a bit
        color: "#e0e0e0",
      },
      ".cm-activeLine": {
        backgroundColor: "rgba(128, 153, 255, 0.1)",
      },
    },
    { dark: true },
  );
}
