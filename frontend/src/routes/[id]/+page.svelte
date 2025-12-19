<script lang="ts">
    import { page } from "$app/state";
    import CodeEditor from "$lib/components/code-editor.svelte";
    import { aura } from "@uiw/codemirror-theme-aura";
    import {
        getLanguageExtension,
        type LanguageType,
    } from "$lib/editor-lang.js";
    import Copy from "$lib/icons/copy.svelte";

    let { data } = $props();
    const MESSAGE_CLEAR_TIMEOUT = 1500;

    let copySuccess = $state(false);

    function shareUrl() {
        copySuccess = false;
        try {
            navigator.clipboard.writeText(page.url.toString());
        } catch (error) {
            console.log(error);
        } finally {
            copySuccess = true;
        }
    }

    $effect(() => {
        let errorTimeout = null;
        if (copySuccess && !errorTimeout) {
            errorTimeout = setTimeout(() => {
                copySuccess = false;
            }, MESSAGE_CLEAR_TIMEOUT);
        }

        return () => {
            errorTimeout = null;
        };
    });
</script>

<svelte:head>
    <title>DevBin | {data.title}</title>
    <meta property="og:title" content={`DevBin | ${data.title}`} />
    <meta
        property="og:image"
        content={page.url.origin + `/paste/${page.params.id}/preview.png`}
    />
</svelte:head>

<div class="flex-col h-full flex">
    {#if copySuccess}
        <div
            class="p-2 rounded-lg border border-green-400 bg-green-500/20 text-green-500 mb-2"
        >
            Link copied
        </div>
    {/if}
    {#if data?.error}
        <div
            class="p-2 rounded-lg border border-red-400 bg-red-500/20 text-red-500 mb-2"
        >
            {data?.error}
        </div>
    {:else if data?.content}
        <div
            class="mb-2 border-2 flex items-center justify-between gap-2 md:flex-row flex-col rounded-lg border-neutral-400 p-2"
        >
            <div class="w-full md:w-fit">
                <h1 class="">
                    title: <span class="font-bold md:text-lg">{data.title}</span
                    >
                </h1>
                <!-- <p class="text-sm">
                    created: {relativeDate(data.created_at)}
                </p>
                <p class="text-sm">
                    expires: {data.expires_at
                        ? relativeDate(data.expires_at)
                        : "never"}
                </p>
                <p class="text-sm">length: {data.content.length}</p> -->
            </div>
            <div class="w-full md:w-fit md:h-full">
                <button
                    class="button-primary w-full justify-between gap-2 p-0 py-0 min-h-fit"
                    onclick={shareUrl}
                >
                    <p class="p-2">{page.url.toString()}</p>
                    <div class="border-l-2 border-white/50 p-1.5">
                        <Copy />
                    </div>
                </button>
            </div>
        </div>
        <div class="gap-2 text-end mb-2"></div>
        <CodeEditor
            value={data?.content}
            extensions={[
                aura,
                getLanguageExtension(data?.file_type || "default"),
            ]}
        />
    {/if}
</div>
