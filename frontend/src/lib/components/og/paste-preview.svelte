<script lang="ts">
    let { title = "Untitled.ts" } = $props();
</script>

<div class="flex flex-col w-full h-full bg-[#121212] font-sans">
    <div
        class="flex items-center w-full h-24 px-10 bg-[#252525] border-b border-[#333]"
    >
        <div class="w-4 h-4 rounded-full bg-[#ff5f56] mr-2"></div>
        <div class="w-4 h-4 rounded-full bg-[#ffbd2e] mr-2"></div>
        <div class="w-4 h-4 rounded-full bg-[#27c93f] mr-10"></div>

        <span class="text-[#858585] text-2xl tracking-tight">{title}</span>
    </div>
</div>
