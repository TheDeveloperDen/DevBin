<script lang="ts">
    import { onMount } from "svelte";
    import { EditorView } from "@codemirror/view";
    import { EditorState } from "@codemirror/state";
    import { editorSetup } from "$lib/editor-setup";
    import { customTheme } from "$lib/editor-theme";
    import { getLanguageExtension, type LanguageType } from "$lib/editor-lang";
    import { shikiToCodeMirror } from "@cmshiki/shiki";
    import { createOnigurumaEngine, getSingletonHighlighter } from "shiki";

    let {
        value = $bindable(""),
        language = "yaml" as LanguageType,
        editable = false,
        theme = "ayu-dark",
    } = $props();

    let editorRef: HTMLDivElement;
    let view: EditorView | null = null;

    // Cache the engine — creating it per-buildEditor call is wasteful
    let enginePromise: ReturnType<typeof createOnigurumaEngine> | null = null;
    function getEngine() {
        enginePromise ??= createOnigurumaEngine(import("shiki/wasm"));
        return enginePromise;
    }

    async function getThemeBg(themeName: string): Promise<string> {
        const highlighter = await getSingletonHighlighter({
            themes: [themeName],
            langs: [],
        });
        return highlighter.getTheme(themeName).bg ?? "#1e1e1e";
    }

    function toShikiLang(lang: LanguageType): string | null {
        return lang === "plain_text" ? null : lang;
    }

    async function buildEditor(doc: string) {
        const shikiLang = toShikiLang(language);

        const [bg, shikiResult] = await Promise.all([
            getThemeBg(theme),
            shikiLang
                ? shikiToCodeMirror({
                      lang: shikiLang,
                      theme,
                      engine: await getEngine(),
                  })
                : Promise.resolve(null),
        ]);

        const themeExtension = EditorView.theme({
            "&": { backgroundColor: bg },
            ".cm-gutters": { backgroundColor: bg, borderRight: "none" },
            ".cm-activeLineGutter": { backgroundColor: `${bg}cc` },
        });

        return new EditorView({
            state: EditorState.create({
                doc,
                extensions: [
                    editorSetup,
                    ...getLanguageExtension(language),
                    customTheme(bg),
                    themeExtension,
                    ...(shikiResult ? [shikiResult.shiki] : []),
                    EditorState.readOnly.of(!editable),
                    EditorView.editable.of(editable),
                ],
            }),
            parent: editorRef,
            dispatchTransactions(trs, view) {
                view.update(trs);
                if (trs.some((tr) => tr.docChanged)) {
                    const newValue = view.state.doc.toString();
                    if (value !== newValue) value = newValue;
                }
            },
        });
    }

    onMount(async () => {
        view = await buildEditor(value);
    });

    $effect(() => {
        const _lang = language;
        const _theme = theme;
        const _editable = editable;
        if (!view) return;
        (async () => {
            const currentDoc = view!.state.doc.toString();
            view!.destroy();
            view = await buildEditor(currentDoc);
        })();
    });
</script>

<div
    bind:this={editorRef}
    class="w-full h-full overflow-scroll"
    spellcheck="false"
></div>

<style>
    :global(.cm-editor) {
        height: 100%;
        outline: none !important;
    }
    :global(.cm-scroller) {
        font-family: "Cascadia Code", "Fira Code", monospace !important;
    }
</style>
