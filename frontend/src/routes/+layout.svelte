<script lang="ts">
    import "./layout.css";
    import favicon from "$lib/assets/devbin-logo.svg";
    import { page } from "$app/state";

    let { children } = $props();
</script>

<svelte:head>
    <title>DevBin</title>
    <link rel="icon" href={favicon} />
    <meta property="og:image" content={page.url.origin + "/devbin-logo.png"} />
    <meta property="og:title" content="DevBin" />
    <meta
        property="og:description"
        content="Paste website for the DevDen discord server"
    />
</svelte:head>

<main class="h-screen max-h-screen max-w-6xl flex flex-col mx-auto p-2">
    <nav class="mb-4">
        <div class="flex flex-row items-center gap-2">
            <img
                src="/devbin-logo.png"
                alt="DevBin Logo"
                class="size-12 md:size-16"
            />
            <h1 class="font-bold">DevBin</h1>
        </div>
    </nav>
    <div class="flex-1 overflow-hidden">
        {@render children()}
    </div>
</main>
