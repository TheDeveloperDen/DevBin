from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from pydantic import BaseModel


class UserMetaData(BaseModel):
    ip: IPv4Address | IPv6Address | Literal["unknown"]
    user_agent: str
