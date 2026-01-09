function isPrivateIP(ip: string): boolean {
    // IPv4 private ranges
    const ipv4PrivateRanges = [
        /^10\./,                                    // 10.0.0.0/8
        /^172\.(1[6-9]|2[0-9]|3[0-1])\./,          // 172.16.0.0/12
        /^192\.168\./,                              // 192.168.0.0/16
        /^127\./,                                   // 127.0.0.0/8 (loopback)
        /^169\.254\./,                              // 169.254.0.0/16 (link-local)
    ];

    // IPv6 private/special addresses
    const ipv6PrivatePatterns = [
        /^::1$/i,                                   // loopback
        /^fc[0-9a-f]{2}:/i,                        // fc00::/7 (unique local)
        /^fd[0-9a-f]{2}:/i,                        // fd00::/8 (unique local)
        /^fe[89ab][0-9a-f]:/i,                     // fe80::/10 (link-local)
    ];

    return ipv4PrivateRanges.some(r => r.test(ip)) || ipv6PrivatePatterns.some(r => r.test(ip));
}

function getPublicIP(ip: string | null | undefined): string | null {
    if (!ip) return null;
    return isPrivateIP(ip) ? null : ip;
}

export function getUserIpAddress(request: Request, getClientAddress: () => string) {
    return getPublicIP(request.headers.get("cf-connecting-ip")) ||
        getPublicIP(request.headers.get("x-real-ip")) ||
        getClientAddress();
}
