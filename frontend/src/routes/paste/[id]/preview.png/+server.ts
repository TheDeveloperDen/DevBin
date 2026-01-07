import {ImageResponse} from "@ethercorps/sveltekit-og";
import SimpleCard from "$lib/components/og/paste-preview.svelte";
import type { RequestHandler } from "@sveltejs/kit";
import { ApiService } from "$lib/api";
import type { Paste } from "$lib/types";
import { API_URL } from "$env/static/private";

export const GET: RequestHandler = async ({params, request, getClientAddress}) => {
    const client_ip = getUserIpAddress(request, getClientAddress);

    const {id} = params;

  if (!id) {
    title = "Paste not found";
    content = "No such paste";
  } else {
    const response = await ApiService.getPasteByUuidPastesPasteIdGet({
      baseUrl: API_URL,
      path: {
        paste_id: id,
      },
      headers: {
        "X-Forwarded-For": client_ip,
      },
    });

    if (!id) {
        title = "Paste not found";
        content = "No such paste";
    } else {
        const response = await ApiService.getPastePastesPasteIdGet({
            baseUrl: API_URL,
            path: {
                paste_id: id,
            },
            headers: {
                "X-Forwarded-For": client_ip,
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
