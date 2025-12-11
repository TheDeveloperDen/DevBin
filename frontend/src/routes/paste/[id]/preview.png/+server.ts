import { ImageResponse } from "@ethercorps/sveltekit-og";
import SimpleCard from "$lib/components/og/paste-preview.svelte";
import type { RequestHandler } from "@sveltejs/kit";
import { genRandomContent } from "$lib/generateRandomText";

export const GET: RequestHandler = async ({ params }) => {
  const { id } = params;

  const content = genRandomContent(id || "");
  const title = id ? `Paste #${id}` : "Default Paste Title";
  const props = {
    title,
    content,
  };
  return new ImageResponse(
    SimpleCard,
    {
      width: 1200,
      height: 630,
    },
    props,
  );
};
