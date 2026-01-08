<script lang="ts">
    import { onMount } from "svelte";
    import { EditorView } from "@codemirror/view";
    import { basicSetup } from "codemirror";
    import { EditorState, StateEffect } from "@codemirror/state";
    import { syntaxHighlighting } from "@codemirror/language";
    import { customTheme, customHighlight } from "$lib/editor-theme";
    import { getLanguageExtension, type LanguageType } from "$lib/editor-lang";

    let {
        value = $bindable(""),
        language = "yaml" as LanguageType,
        editable = false,
    } = $props();

    let editorRef: HTMLDivElement;
    let view: EditorView | null = null;

    let extensionsConfig = $derived([
        basicSetup,
        ...getLanguageExtension(language),
        customTheme,
        syntaxHighlighting(customHighlight),
        EditorState.readOnly.of(!editable),
        EditorView.editable.of(editable),
    ]);

    onMount(() => {
        view = new EditorView({
            state: EditorState.create({
                doc: value,
                extensions: extensionsConfig,
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
    });

    $effect(() => {
        if (view) {
            view.dispatch({
                effects: StateEffect.reconfigure.of(extensionsConfig),
            });
        }
    });
</script>

<div bind:this={editorRef} class="w-full h-full"></div>

<style>
    :global(.cm-editor) {
        height: 100%;
        outline: none !important;
    }

    :global(.cm-scroller) {
        font-family: "Cascadia Code", "Fira Code", monospace !important;
    }
</style>
