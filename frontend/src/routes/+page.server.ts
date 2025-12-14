import { fail } from "@sveltejs/kit";
import type { Actions } from "./$types";
import type { ContentLanguage, ExpiryValues } from "$lib/types";
import { convertExpiryValueToDate } from "$lib/utils/date";
import { ApiService } from "$lib/api";
import { env } from "$env/dynamic/private";

export const actions = {
  paste: async ({ request, getClientAddress }) => {
    const client_ip = getClientAddress();
    const data = await request.formData();
    const title = data.get("title")?.toString() || "";
    const expires_at = data.get("expires_at")?.toString() as ExpiryValues;
    const content = data.get("content")?.toString() || "";
    const content_language =
      data.get("content_language")?.toString() || "plain_text";

    try {
      let expires_at_date = convertExpiryValueToDate(expires_at);
      // clean
      let cleanedformData = {
        title: title.trim(),
        expires_at: expires_at_date,
        content_language: content_language.trim(),
        content: content.trim(),
      };
      console.log(cleanedformData);

      // validate
      if (!cleanedformData.title) {
        return fail(400, {
          title,
          expires_at,
          content,
          content_language,
          error: "Please give your paste a title",
        });
      }
      if (!cleanedformData.content) {
        return fail(400, {
          title,
          expires_at,
          content,
          content_language,
          error: "Please input your paste content",
        });
      }

      const response = await ApiService.createPastePastesPost({
        baseUrl: env.API_BASE_URL,
        body: {
          title: cleanedformData.title,
          content: cleanedformData.content,
          content_language: cleanedformData.content_language as ContentLanguage,
          expires_at: cleanedformData.expires_at,
        },
        headers: {
          "X-Forwarded-For": client_ip,
        },
      });

      if (response.error) {
        console.log(response.error);
        return fail(400, {
          title,
          expires_at,
          content,
          content_language,
          error: response.error.detail || "Something went wrong",
        });
      }
      console.log(response.data);

      const data = response.data as object;
      return {
        ...data,
        success: true,
      };
    } catch (error) {
      console.log(error);
      error =
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again";
      return fail(500, { error });
    }
  },
} satisfies Actions;
