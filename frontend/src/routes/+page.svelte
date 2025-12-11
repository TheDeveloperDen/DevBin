<script lang="ts">
    import type { ExpiryValues } from "$lib/types";
    import type { PageProps } from "./$types";
    import { enhance, applyAction } from "$app/forms";
    import { goto } from "$app/navigation";

    const ERROR_CLEAR_TIMEOUT = 2500;
    const MAX_PASTE_CONTENT_LENGTH = 10000;

    let { form }: PageProps = $props();

    interface FormData {
        title: string;
        expires_in: ExpiryValues;
        content: string;
    }
    let formData: FormData = $state({
        title: "",
        expires_in: "never",
        content: "",
    });
    let errorMessage = $state("");
    let success = $state(false);

    function handleSubmit() {
        try {
            let cleanedformData: FormData = {
                title: formData.title.trim(),
                expires_in: formData.expires_in,
                content: formData.content.trim(),
            };
            // validate data
            if (!cleanedformData.title) {
                errorMessage = "Please give your paste a title";
                return;
            }
            if (!cleanedformData.content) {
                errorMessage = "Please input your paste content";
                return;
            }
            success = true;
        } catch (error) {
            console.log(error);
            error =
                error instanceof Error
                    ? error.message
                    : "Something went wrong. Please try again";
        } finally {
        }
    }

    $effect(() => {
        let errorTimeout = null;
        if (errorMessage && !errorTimeout) {
            errorTimeout = setTimeout(() => {
                errorMessage = "";
            }, ERROR_CLEAR_TIMEOUT);
        }

        return () => {
            errorTimeout = null;
        };
    });
</script>

<form
    method="POST"
    action="?/paste"
    class="flex flex-col h-full flex-1"
    use:enhance={({ formElement }) => {
        return async ({ result }) => {
            console.log(result);
            if (result.type === "success" && result.data && result.data?.id) {
                goto(`paste/${result.data.id as string}`);
            } else {
                applyAction(result);
            }
        };
    }}
>
    {#if form?.error}
        <div
            class="p-2 rounded-lg border border-red-400 bg-red-500/20 text-red-500 mb-2"
        >
            {form?.error}
        </div>
    {/if}
    {#if form?.success}
        <div
            class="p-2 rounded-lg border border-green-400 bg-green-500/20 text-green-500 mb-2"
        >
            Paste Created Successfully!
        </div>
    {/if}
    <div class="flex flex-col md:flex-row gap-4 mb-4">
        <input
            title="paste title"
            class="input flex-1"
            placeholder="Enter a title for your paste"
            name="title"
            value={form?.title}
        />
        <button type="submit" title="create paste" class="button-primary"
            >Create Paste</button
        >
        <div
            class="md:justify-normal justify-between flex flex-row items-center gap-2"
        >
            <label for="expires_at">Expires in</label>
            <select
                title="paste expiry period"
                class="input"
                value={form?.expires_at}
                name="expires_at"
            >
                <option value="never">never</option>
                <option value="5m">5 minutes</option>
                <option value="15m">15 minutes</option>
                <option value="30m">30 minutes</option>
                <option value="1h">1 hour</option>
                <option value="3h">3 hours</option>
                <option value="1d">1 day</option>
            </select>
        </div>
    </div>
    <div class="flex-1 flex gap-2 flex-col">
        <div class="flex items-center justify-between">
            <select
                title="content language"
                class="input"
                value={form?.content_language}
                name="content_language"
            >
                <option value="plain_text">plaintext</option>
            </select>
            <p class="text-end">
                {formData.content.trim()
                    .length}/{MAX_PASTE_CONTENT_LENGTH.toLocaleString()}
            </p>
        </div>
        <textarea
            title="paste content"
            name="content"
            value={form?.content}
            maxlength={MAX_PASTE_CONTENT_LENGTH}
            placeholder="Your awesome content....."
            class="input flex-1"
        ></textarea>
    </div>
</form>
