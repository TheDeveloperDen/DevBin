"""Unit tests for IP utility functions."""

import pytest
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from app.utils.ip import (
    is_ip_in_trusted_hosts,
    parse_ip_or_network,
    validate_ip_address,
)


@pytest.mark.unit
class TestValidateIPAddress:
    """Tests for validate_ip_address function."""

    def test_valid_ipv4_address(self):
        """Should parse valid IPv4 addresses."""
        result = validate_ip_address("192.168.1.1")
        assert result == IPv4Address("192.168.1.1")

    def test_valid_ipv6_address(self):
        """Should parse valid IPv6 addresses."""
        result = validate_ip_address("::1")
        assert result == IPv6Address("::1")

    def test_invalid_address_returns_none(self):
        """Should return None for invalid IP addresses."""
        assert validate_ip_address("invalid") is None
        assert validate_ip_address("256.256.256.256") is None
        assert validate_ip_address("") is None


@pytest.mark.unit
class TestParseIPOrNetwork:
    """Tests for parse_ip_or_network function."""

    def test_parse_single_ipv4_address(self):
        """Should parse single IPv4 address."""
        result = parse_ip_or_network("127.0.0.1")
        assert result == IPv4Address("127.0.0.1")

    def test_parse_single_ipv6_address(self):
        """Should parse single IPv6 address."""
        result = parse_ip_or_network("::1")
        assert result == IPv6Address("::1")

    def test_parse_ipv4_network_cidr(self):
        """Should parse IPv4 network in CIDR notation."""
        result = parse_ip_or_network("10.0.0.0/8")
        assert result == IPv4Network("10.0.0.0/8")

    def test_parse_ipv4_network_non_strict(self):
        """Should parse non-strict CIDR (host bits set)."""
        result = parse_ip_or_network("10.5.3.1/8")
        assert result == IPv4Network("10.0.0.0/8")

    def test_parse_ipv6_network_cidr(self):
        """Should parse IPv6 network in CIDR notation."""
        result = parse_ip_or_network("fd00::/8")
        assert result == IPv6Network("fd00::/8")

    def test_parse_common_private_networks(self):
        """Should parse common private network ranges."""
        assert parse_ip_or_network("10.0.0.0/8") == IPv4Network("10.0.0.0/8")
        assert parse_ip_or_network("172.16.0.0/12") == IPv4Network("172.16.0.0/12")
        assert parse_ip_or_network("192.168.0.0/16") == IPv4Network("192.168.0.0/16")

    def test_invalid_input_returns_none(self):
        """Should return None for invalid input."""
        assert parse_ip_or_network("invalid") is None
        assert parse_ip_or_network("10.0.0.0/99") is None
        assert parse_ip_or_network("") is None


@pytest.mark.unit
class TestIsIPInTrustedHosts:
    """Tests for is_ip_in_trusted_hosts function."""

    def test_ip_matches_exact_address(self):
        """Should match exact IP address in trusted list."""
        trusted = [IPv4Address("127.0.0.1")]
        assert is_ip_in_trusted_hosts("127.0.0.1", trusted) is True
        assert is_ip_in_trusted_hosts("192.168.1.1", trusted) is False

    def test_ip_in_network_range(self):
        """Should match IP within a trusted network range."""
        trusted = [IPv4Network("10.0.0.0/8")]

        assert is_ip_in_trusted_hosts("10.0.0.1", trusted) is True
        assert is_ip_in_trusted_hosts("10.255.255.255", trusted) is True
        assert is_ip_in_trusted_hosts("10.50.100.200", trusted) is True
        assert is_ip_in_trusted_hosts("11.0.0.1", trusted) is False

    def test_mixed_addresses_and_networks(self):
        """Should handle mix of individual IPs and networks."""
        trusted = [
            IPv4Address("127.0.0.1"),
            IPv4Network("10.0.0.0/8"),
            IPv4Network("172.16.0.0/12"),
        ]

        assert is_ip_in_trusted_hosts("127.0.0.1", trusted) is True
        assert is_ip_in_trusted_hosts("10.5.3.1", trusted) is True
        assert is_ip_in_trusted_hosts("172.20.0.1", trusted) is True
        assert is_ip_in_trusted_hosts("192.168.1.1", trusted) is False
        assert is_ip_in_trusted_hosts("8.8.8.8", trusted) is False

    def test_ipv6_network(self):
        """Should handle IPv6 networks."""
        trusted = [IPv6Network("fd00::/8")]

        assert is_ip_in_trusted_hosts("fd00::1", trusted) is True
        assert is_ip_in_trusted_hosts("fd12:3456::1", trusted) is True
        assert is_ip_in_trusted_hosts("fe80::1", trusted) is False

    def test_accepts_string_ip(self):
        """Should accept IP as string."""
        trusted = [IPv4Network("192.168.0.0/16")]
        assert is_ip_in_trusted_hosts("192.168.1.100", trusted) is True

    def test_accepts_ip_address_object(self):
        """Should accept IP address object."""
        trusted = [IPv4Network("192.168.0.0/16")]
        ip = IPv4Address("192.168.1.100")
        assert is_ip_in_trusted_hosts(ip, trusted) is True

    def test_invalid_ip_string_returns_false(self):
        """Should return False for invalid IP string."""
        trusted = [IPv4Network("10.0.0.0/8")]
        assert is_ip_in_trusted_hosts("invalid", trusted) is False
        assert is_ip_in_trusted_hosts("", trusted) is False

    def test_empty_trusted_list_returns_false(self):
        """Should return False when trusted list is empty."""
        assert is_ip_in_trusted_hosts("10.0.0.1", []) is False

    def test_ipv4_not_in_ipv6_network(self):
        """IPv4 address should not match IPv6 network."""
        trusted = [IPv6Network("fd00::/8")]
        assert is_ip_in_trusted_hosts("10.0.0.1", trusted) is False

    def test_ipv6_not_in_ipv4_network(self):
        """IPv6 address should not match IPv4 network."""
        trusted = [IPv4Network("10.0.0.0/8")]
        assert is_ip_in_trusted_hosts("::1", trusted) is False
