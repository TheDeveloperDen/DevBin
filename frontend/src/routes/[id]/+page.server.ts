import { ApiService } from "$lib/api/index.js";
import type { LanguageType } from "$lib/editor-lang.js";
import { env } from "$env/dynamic/private";

export async function load({ params, getClientAddress }) {
  const client_ip = getClientAddress();
  const { id: paste_id } = params;

  try {
    const file_keys = paste_id.split(".");
    const file_name = file_keys[0];
    const file_type = file_keys[1] || "";
    const response = await ApiService.getLegacyPastePastesLegacyPasteIdGet({
      baseUrl: env.API_URL,
      path: {
        paste_id: file_name,
      },
      headers: {
        "X-Forwarded-For": client_ip,
      },
    });

    if (!response.data) {
      return { error: "Paste not found or is currently unavailable" };
    }

    return {
      title: file_name,
      content: response.data.content,
      file_type: file_type as LanguageType,
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
