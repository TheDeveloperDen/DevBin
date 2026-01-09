<script lang="ts">
    import { applyAction, enhance } from "$app/forms";
    import { page } from "$app/state";
    import CodeEditor from "$lib/components/code-editor.svelte";
    import {
        getLanguageExtension,
        type LanguageType,
    } from "$lib/editor-lang.js";
    import Copy from "$lib/icons/copy.svelte";
    import Delete from "$lib/icons/delete.svelte";
    import Edit from "$lib/icons/edit.svelte";
    import { relativeDate } from "$lib/utils/date";

    let { data, form } = $props();
    const MESSAGE_CLEAR_TIMEOUT = 1500;

    let editorValue = $derived(data?.content || "");
    let deletePrompt = $state(false);
    let isEditing = $state(false);
    let copySuccess = $state(false);
    let showStatusMessage = $state(true);
    let embed = page.url.searchParams.get("embed") || false;

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
        const hasNewMessage =
            form?.success || form?.error || data?.error || copySuccess;

        if (hasNewMessage) {
            showStatusMessage = true;

            const timer = setTimeout(() => {
                showStatusMessage = false;
                copySuccess = false;
            }, MESSAGE_CLEAR_TIMEOUT);

            return () => clearTimeout(timer);
        }
    });
</script>

<svelte:head>
    <title>DevBin | {data.title}</title>
    <meta property="og:title" content={`DevBin | ${data.title}`} />
    <meta
        property="og:image"
        content={page.url.origin + `/paste/${data.id}/preview.png`}
    />
</svelte:head>

{#if embed}
    <CodeEditor value={data?.content || ""} />
{:else}
    <form
        class="flex-col h-full flex"
        method="POST"
        use:enhance={async ({ action, formData, formElement }) => {
            formData.set("content", editorValue.toString());

            return async ({ result }) => {
                console.log(result);
                applyAction(result);
            };
        }}
    >
        <!-- status messages -->
        {#if showStatusMessage}
            {#if copySuccess}
                <div
                    class="p-2 rounded-lg border border-green-400 bg-green-500/20 text-green-500 mb-2"
                >
                    Link copied
                </div>
            {/if}

            {#if form?.success}
                <div
                    class="p-2 rounded-lg border border-green-400 bg-green-500/20 text-green-500 mb-2"
                >
                    {form?.message}
                </div>
            {/if}

            {#if form?.error || data?.error}
                <div
                    class="p-2 rounded-lg border border-red-400 bg-red-500/20 text-red-500 mb-2"
                >
                    {form?.error || data?.error}
                </div>
            {/if}
        {/if}

        <!-- main content -->
        {#if data?.content}
            <input class="hidden" value={data?.id} name="id" />
            <div
                class="mb-2 flex items-center justify-between gap-2 md:flex-row flex-col rounded-lg p-2"
            >
                <div class="w-full md:w-fit">
                    <h1 class="">
                        title: <span class="font-bold md:text-lg"
                            >{data.title}</span
                        >
                    </h1>
                    <p class="text-sm">
                        created: {relativeDate(data.created_at)}
                    </p>
                    <p class="text-sm">
                        expires: {data.expires_at
                            ? relativeDate(data.expires_at)
                            : "never"}
                    </p>
                    <p class="text-sm">length: {data.content.length}</p>
                </div>
                <div
                    class="w-full md:w-fit md:h-full flex flex-col gap-2 items-end"
                >
                    <button
                        class="button-primary w-full justify-between gap-2 p-0 pl-2 py-0 min-h-fit"
                        onclick={shareUrl}
                        type="button"
                    >
                        <p
                            class="line-clamp-1 text-start break-all text-ellipsis"
                        >
                            {page.url.toString()}
                        </p>
                        <div class="border-l-2 border-white/50 p-1.5">
                            <Copy />
                        </div>
                    </button>
                    {#if data.edit_token && data.delete_token}
                        <div class:hidden={!deletePrompt}>
                            <p>Are you sure you want to delete this paste?</p>
                        </div>
                        <div class="flex flex-row gap-2">
                            <!-- edit actions -->
                            <button
                                onclick={() => (isEditing = false)}
                                class="button-primary"
                                formaction="?/edit"
                                class:hidden={!isEditing}
                            >
                                Save
                            </button>
                            <button
                                type={"button"}
                                onclick={() => (isEditing = !isEditing)}
                                class={`${isEditing ? "button-ghost" : "button-primary"}`}
                                class:hidden={deletePrompt}
                            >
                                {#if isEditing}
                                    Cancel
                                {:else}
                                    <Edit />
                                {/if}
                            </button>

                            <!-- delete actions -->
                            <button
                                onclick={() => (deletePrompt = true)}
                                class="button-danger"
                                formaction="?/delete"
                                class:hidden={!deletePrompt}
                            >
                                Confirm
                            </button>
                            <button
                                onclick={() => (deletePrompt = !deletePrompt)}
                                class={`${deletePrompt ? "button-outline" : "button-danger"}`}
                                type="button"
                                class:hidden={isEditing}
                            >
                                {#if deletePrompt}
                                    Cancel
                                {:else}
                                    <Delete />
                                {/if}
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
            <div class="gap-2 text-end mb-2"></div>
            <div class="flex-1 overflow-y-scroll rounded-lg p-2">
                <CodeEditor
                    bind:value={editorValue}
                    editable={(!!data?.edit_token && isEditing) || false}
                    language={data?.content_language as LanguageType}
                />
            </div>
        {/if}
    </form>
{/if}
