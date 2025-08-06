"""Data Transfer Objects for device operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FindDeviceRequest:
    """Request DTO for finding a device."""
    ip: Optional[str] = None  # Explicitly provided IP
    network_range: Optional[str] = None
    open_in_browser: bool = False


@dataclass
class FindDeviceResponse:
    """Response DTO for finding a device."""
    found: bool
    ip: Optional[str] = None  # Simplified name
    ip_address: Optional[str] = None  # Keep for compatibility
    port: Optional[str] = None
    url: Optional[str] = None
    device_name: Optional[str] = None
    source: Optional[str] = None  # "provided", "network", "stored"
    
    @classmethod
    def not_found(cls) -> 'FindDeviceResponse':
        """Create a response for when no device is found."""
        return cls(found=False)
    
    @classmethod
    def success(cls, ip: str, port: str, url: str, name: str, source: str = "network") -> 'FindDeviceResponse':
        """Create a successful response."""
        return cls(
            found=True,
            ip=ip,
            ip_address=ip,  # Duplicate for compatibility
            port=port,
            url=url,
            device_name=name,
            source=source
        )