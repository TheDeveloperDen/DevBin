export function getUserIpAddress(request: Request, getClientAddress: () => string) {
    return request.headers.get("x-real-ip") ||
        request.headers.get("cf-connecting-ip") || // Cloudflare
        request.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
        getClientAddress();
}