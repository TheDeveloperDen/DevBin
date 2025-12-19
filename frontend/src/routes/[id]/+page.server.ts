import type { LanguageType } from "$lib/editor-lang.js";
import axios from "axios";

export async function load({ params, getClientAddress }) {
  const { id: paste_id } = params;

  try {
    const file_keys = paste_id.split(".");
    const file_name = file_keys[0];
    const file_type = file_keys[1] || "";
    const response = await axios.get(
      `https://paste.bristermitten.me/documents/${file_name}`,
    );

    if (!response.data) {
      return { error: "Paste not found or is currently unavailable" };
    }

    return {
      title: response.data.key,
      content: response.data.data,
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
