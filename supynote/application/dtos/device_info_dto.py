"""DTOs for the Device Info use case."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfoRequest:
    """Request DTO for getting device information."""
    
    ip: Optional[str] = None
    port: str = "8089"
    output_directory: Optional[str] = None


@dataclass
class DeviceInfoResponse:
    """Response DTO for device information."""
    
    success: bool
    ip: Optional[str] = None
    port: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    output_directory: Optional[str] = None
    message: Optional[str] = None
    
    @classmethod
    def success_with_info(
        cls,
        ip: str,
        port: str,
        output_directory: Optional[str] = None
    ) -> "DeviceInfoResponse":
        """Create a success response with device info."""
        return cls(
            success=True,
            ip=ip,
            port=port,
            url=f"http://{ip}:{port}",
            status="🟢 Connected",
            output_directory=output_directory
        )
    
    @classmethod
    def device_not_found(cls) -> "DeviceInfoResponse":
        """Create a response when no device was found."""
        return cls(
            success=False,
            message="❌ No Supernote device found. Use --ip to specify manually."
        )