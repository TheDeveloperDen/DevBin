from slowapi import Limiter
from starlette.requests import Request


def get_ip_address(request: Request):
    return str(request.state.user_metadata.ip)


limiter = Limiter(key_func=get_ip_address)
