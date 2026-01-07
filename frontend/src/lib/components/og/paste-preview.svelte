<script lang="ts">
    let data = $props();

    let { title, content } = data;

    const MAX_LENGTH = 300;
    const truncatedContent =
        content.length > MAX_LENGTH
            ? content.substring(0, MAX_LENGTH) + "..."
            : content;
</script>

<div
    class="flex flex-col justify-center items-center w-full relative h-full bg-neutral-900 p-[50px] font-sans"
>
    <div class="w-full flex justify-center mb-2">
        <h1 class="text-white text-6xl">
            {title}
        </h1>
    </div>

    <div
        class="flex flex-row justify-start items-center w-full overflow-hidden pl-5"
    >
        <p
            class="text-neutral-500 text-3xl text-left leading-tight overflow-hidden"
        >
            {truncatedContent}
        </p>
    </div>
</div>
