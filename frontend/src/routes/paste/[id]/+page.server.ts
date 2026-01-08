import { API_URL } from "$env/static/private";
import { ApiService } from "$lib/api";
import type { Paste } from "$lib/types";
import { env } from "$env/dynamic/private";
import { getUserIpAddress } from "$lib/utils/ip";
import type { Actions } from "./$types";
import { fail, redirect } from "@sveltejs/kit";

export async function load({ params, request, getClientAddress, cookies }) {
  const client_ip = getUserIpAddress(request, getClientAddress);
  const { id: paste_id } = params;

  const tokens: { edit_token: string; delete_token: string } = JSON.parse(
    cookies.get(paste_id) || "",
  );

  try {
    const response = await ApiService.getPasteByUuidPastesPasteIdGet({
      baseUrl: env.API_URL,
      path: {
        paste_id: paste_id,
      },
      headers: {
        "X-Forwarded-For": client_ip,
      },
    });

    if (!response.data) {
      return { error: "Paste not found or is currently unavailable" };
    }

    if (response.error) {
      console.log(response.error);
      return { error: response.error?.detail };
    }

    const { id, title, content, content_language, expires_at, created_at } =
      JSON.parse(JSON.stringify(response.data)) as Paste;
    return {
      id,
      title,
      content_language,
      content,
      expires_at,
      created_at,
      edit_token: tokens.edit_token,
      delete_token: tokens.delete_token,
    };
  } catch (error) {
    console.log("Load error:", error);
    error =
      error instanceof Error
        ? error.message
        : "Something went wrong. Please try again";
    return { error };
  }
}

export const actions = {
  edit: async ({ cookies, request }) => {
    const data = await request.formData();
    const paste_id = data.get("id")?.toString() || "";
    const paste_content = data.get("content")?.toString() || "";
    const tokens: { edit_token: string; delete_token: string } = JSON.parse(
      cookies.get(paste_id) || "",
    );

    const response = await ApiService.editPastePastesPasteIdPut({
      path: {
        paste_id,
      },
      body: {
        content: paste_content,
      },
      headers: {
        Authorization: tokens.edit_token,
      },
    });

    if (response.error) {
      return fail(400, {
        content: paste_content,
        error: response.error.detail,
      });
    }

    return { success: true, message: "Paste saved", content: paste_content };
  },
  delete: async ({ cookies, request }) => {
    const data = await request.formData();
    const paste_id = data.get("id")?.toString() || "";
    const tokens: { edit_token: string; delete_token: string } = JSON.parse(
      cookies.get(paste_id) || "",
    );
    const response = await ApiService.deletePastePastesPasteIdDelete({
      path: {
        paste_id,
      },
      headers: {
        Authorization: tokens.delete_token,
      },
    });

    if (response.error) {
      return fail(400, {
        error: response.error.detail,
      });
    }

    return redirect(303, "/");
  },
} satisfies Actions;
