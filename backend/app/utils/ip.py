import ipaddress
import socket
from ipaddress import IPv4Address, IPv6Address


def resolve_hostname(hostname):
    try:
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror as e:
        print(f"Error resolving {hostname}: {e}")
        return None


def validate_ip_address(ip_address: str) -> IPv4Address | IPv6Address | None:
    try:
        ip_address = ipaddress.ip_address(ip_address)
        return ip_address
    except ValueError:
        return None
