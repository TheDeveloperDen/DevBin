import {ApiService} from "$lib/api";
import type {Paste} from "$lib/types";
import {env} from "$env/dynamic/private";

export async function load({params, request, getClientAddress}) {
    const client_ip =
        request.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
        request.headers.get("x-real-ip") ||
        request.headers.get("cf-connecting-ip") || // Cloudflare
        getClientAddress();
    const {id: paste_id} = params;

    try {
        const response = await ApiService.getPastePastesPasteIdGet({
            baseUrl: env.API_BASE_URL,
            path: {
                paste_id: paste_id,
            },
            headers: {
                "X-Forwarded-For": client_ip,
            },
        });

        if (!response.data) {
            return {error: "Paste not found or is currently unavailable"};
        }

        if (response.error) {
            console.log(response.error);
            return {error: response.error?.detail};
        }

        const {id, title, content, content_language, expires_at, created_at} =
            JSON.parse(JSON.stringify(response.data)) as Paste;
        return {
            id,
            title,
            content_language,
            content,
            expires_at,
            created_at,
        };
    } catch (error) {
        console.log("Load error:", error);
        error =
            error instanceof Error
                ? error.message
                : "Something went wrong. Please try again";
        return {error};
    }
}
