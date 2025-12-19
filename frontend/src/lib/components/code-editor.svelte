<script lang="ts">
    import { EditorView, basicSetup } from "codemirror";
    import { EditorState, type Extension } from "@codemirror/state";
    import { onMount, onDestroy } from "svelte";

    interface EditorProps {
        value: string;
        extensions?: Extension[];
    }

    let { value = $bindable(""), extensions = [] }: EditorProps = $props();

    let editorRef: HTMLDivElement;
    let view: EditorView | null = null;

    const baseExtensions: Extension[] = [
        basicSetup,
        EditorState.allowMultipleSelections.of(true),
    ];

    function initializeEditor() {
        const state = EditorState.create({
            doc: value,
            extensions: [...baseExtensions, ...extensions],
        });

        view = new EditorView({
            state,
            parent: editorRef,
            dispatchTransactions(trs, view) {
                view.update(trs);
                if (trs.some((tr) => tr.docChanged)) {
                    value = view.state.doc.toString();
                }
            },
        });
    }

    onMount(() => {
        initializeEditor();
    });

    onDestroy(() => {
        view?.destroy();
        view = null;
    });

    $effect(() => {
        if (view && value !== view.state.doc.toString()) {
            view.dispatch({
                changes: { from: 0, to: view.state.doc.length, insert: value },
            });
        }
    });
</script>

<div class="h-full w-full overflow-hidden" bind:this={editorRef}></div>
