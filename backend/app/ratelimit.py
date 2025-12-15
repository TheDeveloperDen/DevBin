from slowapi import Limiter
from starlette.requests import Request


def get_ip_address(request: Request):
    print(request.headers)
    print(request.client)
    if request.headers.get("X-Forwarded-For", None):
        return request.headers.get("X-Forwarded-For")
    if not request.client or not request.client.host:
        return "127.0.0.1"

    return request.client.host


limiter = Limiter(key_func=get_ip_address)
