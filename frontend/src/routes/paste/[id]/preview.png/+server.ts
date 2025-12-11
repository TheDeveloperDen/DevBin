import { ImageResponse } from "@ethercorps/sveltekit-og";
import SimpleCard from "$lib/components/og/paste-preview.svelte";
import type { RequestHandler } from "@sveltejs/kit";
import { ApiService } from "$lib/api";
import type { Paste } from "$lib/types";

export const GET: RequestHandler = async ({ params }) => {
  const { id } = params;

  let title = "";
  let content = "";

  if (!id) {
    title = "Paste not found";
    content = "No such paste";
  } else {
    const response = await ApiService.getPastePastesPasteIdGet({
      path: {
        paste_id: id,
      },
    });

    if (response.data) {
      const data = response.data as Paste;
      ((title = data.title), (content = data.content.slice(0, 200)));
    }
  }

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
