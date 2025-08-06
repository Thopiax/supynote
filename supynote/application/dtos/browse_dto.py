"""DTOs for the Browse Device use case."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowseDeviceRequest:
    """Request DTO for browsing a device."""
    
    ip: Optional[str] = None
    port: str = "8089"
    open_in_browser: bool = True


@dataclass 
class BrowseDeviceResponse:
    """Response DTO for browsing a device."""
    
    success: bool
    url: Optional[str] = None
    device_ip: Optional[str] = None
    message: str = ""
    
    @classmethod
    def success_opened(cls, url: str, device_ip: str) -> "BrowseDeviceResponse":
        """Create a success response when browser was opened."""
        return cls(
            success=True,
            url=url,
            device_ip=device_ip,
            message=f"🌐 Opening {url} in browser..."
        )
    
    @classmethod
    def device_not_found(cls) -> "BrowseDeviceResponse":
        """Create a response when no device was found."""
        return cls(
            success=False,
            message="❌ No Supernote device found. Use --ip to specify manually."
        )