import ipaddress
import socket
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

type IPAddress = IPv4Address | IPv6Address
type IPNetwork = IPv4Network | IPv6Network
type TrustedHost = IPAddress | IPNetwork


def resolve_hostname(hostname: str) -> str | None:
    try:
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror as e:
        print(f"Error resolving {hostname}: {e}")
        return None


def validate_ip_address(ip_address: str) -> IPAddress | None:
    try:
        return ipaddress.ip_address(ip_address)
    except ValueError:
        return None


def parse_ip_or_network(value: str) -> TrustedHost | None:
    """Parse a string as either an IP address or a network (CIDR notation).

    Examples:
        - "192.168.1.1" -> IPv4Address
        - "10.0.0.0/8" -> IPv4Network
        - "::1" -> IPv6Address
        - "fd00::/8" -> IPv6Network
    """
    # Try as network first (handles both "10.0.0.0/8" and "10.0.0.1" as /32)
    if "/" in value:
        try:
            return ipaddress.ip_network(value, strict=False)
        except ValueError:
            return None

    # Try as single IP address
    return validate_ip_address(value)


def is_ip_in_trusted_hosts(ip: IPAddress | str, trusted_hosts: list[TrustedHost]) -> bool:
    """Check if an IP address is in the list of trusted hosts/networks."""
    if isinstance(ip, str):
        parsed_ip = validate_ip_address(ip)
        if parsed_ip is None:
            return False
        ip = parsed_ip

    for trusted in trusted_hosts:
        if isinstance(trusted, (IPv4Network, IPv6Network)):
            # Check if IP is within the network
            try:
                if ip in trusted:
                    return True
            except TypeError:
                # IPv4 address can't be in IPv6 network and vice versa
                continue
        elif ip == trusted:
            return True

    return False
