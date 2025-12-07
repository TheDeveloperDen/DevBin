<script lang="ts">
    import { page } from "$app/state";

    let { data } = $props();
    const MESSAGE_CLEAR_TIMEOUT = 1500;

    function formatDate(date: Date | string) {
        return new Date(date).toLocaleString("en-US", {
            dateStyle: "long",
            timeStyle: "medium",
        });
    }

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
            Link copied Successfully
        </div>
    {/if}
    <div
        class="mb-2 border-2 flex items-center justify-between gap-2 md:flex-row flex-col rounded-lg border-neutral-400 p-2"
    >
        <div class="w-full md:w-fit">
            <h1 class="">
                title: <span class="font-bold md:text-lg">{data.title}</span>
            </h1>
            <p class="text-sm">
                created: {formatDate(data.created_at)}
            </p>
            <p class="text-sm">expires: {formatDate(data.expires_at)}</p>
            <p class="text-sm">length: {data.content.length}</p>
        </div>
        <div class="w-full md:w-fit md:h-full">
            <button
                class="button-primary w-full justify-between gap-2 p-0 py-0 min-h-fit"
                onclick={shareUrl}
            >
                <p class="p-2">{page.url.toString()}</p>
                <div class="border-l p-1.5">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="size-6"
                        viewBox="0 0 24 24"
                    >
                        <path
                            fill="currentColor"
                            d="M15.24 2h-3.894c-1.764 0-3.162 0-4.255.148c-1.126.152-2.037.472-2.755 1.193c-.719.721-1.038 1.636-1.189 2.766C3 7.205 3 8.608 3 10.379v5.838c0 1.508.92 2.8 2.227 3.342c-.067-.91-.067-2.185-.067-3.247v-5.01c0-1.281 0-2.386.118-3.27c.127-.948.413-1.856 1.147-2.593s1.639-1.024 2.583-1.152c.88-.118 1.98-.118 3.257-.118h3.07c1.276 0 2.374 0 3.255.118A3.6 3.6 0 0 0 15.24 2"
                        />
                        <path
                            fill="currentColor"
                            d="M6.6 11.397c0-2.726 0-4.089.844-4.936c.843-.847 2.2-.847 4.916-.847h2.88c2.715 0 4.073 0 4.917.847S21 8.671 21 11.397v4.82c0 2.726 0 4.089-.843 4.936c-.844.847-2.202.847-4.917.847h-2.88c-2.715 0-4.073 0-4.916-.847c-.844-.847-.844-2.21-.844-4.936z"
                        />
                    </svg>
                </div>
            </button>
        </div>
    </div>
    <div class="gap-2 text-end mb-2"></div>
    <div
        class="flex-1 overflow-y-scroll border-2 rounded-lg border-neutral-400 p-2"
    >
        <p>{data.content}</p>
    </div>
</div>
