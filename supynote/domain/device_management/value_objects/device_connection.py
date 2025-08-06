"""Device connection value object."""

import re
from typing import Optional

from ...shared.base_value_object import ValueObject


class IPAddress(ValueObject):
    """IP address value object."""
    
    def __init__(self, address: str):
        self._validate_ip(address)
        self._address = address
    
    @property
    def value(self) -> str:
        """Get the IP address."""
        return self._address
    
    def _validate_ip(self, address: str) -> None:
        """Validate IP address format."""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, address):
            raise ValueError(f"Invalid IP address: {address}")
        
        # Check each octet is 0-255
        octets = address.split('.')
        for octet in octets:
            if int(octet) > 255:
                raise ValueError(f"Invalid IP address: {address}")
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IPAddress):
            return False
        return self._address == other._address
    
    def __hash__(self) -> int:
        return hash(self._address)
    
    def __str__(self) -> str:
        return self._address


class Port(ValueObject):
    """Network port value object."""
    
    def __init__(self, port: int):
        self._validate_port(port)
        self._port = port
    
    @property
    def value(self) -> int:
        """Get the port number."""
        return self._port
    
    def _validate_port(self, port: int) -> None:
        """Validate port number."""
        if not isinstance(port, int):
            raise ValueError(f"Port must be an integer, got {type(port)}")
        if port < 1 or port > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Port):
            return False
        return self._port == other._port
    
    def __hash__(self) -> int:
        return hash(self._port)
    
    def __str__(self) -> str:
        return str(self._port)


class DeviceConnection(ValueObject):
    """Device connection information."""
    
    def __init__(self, ip_address: IPAddress, port: Port):
        self._ip_address = ip_address
        self._port = port
    
    @classmethod
    def from_strings(cls, ip: str, port_str: str) -> 'DeviceConnection':
        """Create from string values."""
        return cls(
            IPAddress(ip),
            Port(int(port_str))
        )
    
    @classmethod
    def for_discovery(cls, port: int = 8089) -> 'DeviceConnection':
        """Create a connection for device discovery (no IP yet)."""
        # Use a placeholder IP for discovery phase
        # This will be replaced when actual device is found
        return cls(
            IPAddress("0.0.0.0"),  # Placeholder
            Port(port)
        )
    
    @property
    def ip_address(self) -> IPAddress:
        """Get the IP address."""
        return self._ip_address
    
    @property
    def port(self) -> Port:
        """Get the port."""
        return self._port
    
    @property
    def url(self) -> str:
        """Get the full URL for this connection."""
        return f"http://{self._ip_address}:{self._port}"
    
    @property
    def value(self) -> tuple:
        """Get the connection as a tuple."""
        return (self._ip_address, self._port)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DeviceConnection):
            return False
        return (self._ip_address == other._ip_address and 
                self._port == other._port)
    
    def __hash__(self) -> int:
        return hash((self._ip_address, self._port))
    
    def __str__(self) -> str:
        return f"{self._ip_address}:{self._port}"
    
    def __repr__(self) -> str:
        return f"DeviceConnection({self._ip_address}, {self._port})"