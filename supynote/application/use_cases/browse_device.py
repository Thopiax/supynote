"""Use case for browsing a device in web browser."""
import webbrowser
from typing import Optional

from ..dtos.browse_dto import BrowseDeviceRequest, BrowseDeviceResponse
from ...domain.device_management.repositories.device_repository import DeviceRepository
from ...domain.device_management.value_objects.device_connection import DeviceConnection
from ...infrastructure.network.network_discovery_service import NetworkDiscoveryService


class BrowseDeviceUseCase:
    """Use case for opening device web interface in browser."""
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        discovery_service: NetworkDiscoveryService
    ):
        """Initialize the use case."""
        self._device_repository = device_repository
        self._discovery_service = discovery_service
    
    def execute(self, request: BrowseDeviceRequest) -> BrowseDeviceResponse:
        """
        Execute the browse device use case.
        
        1. Find or discover device
        2. Build URL
        3. Open in browser
        """
        # Try to find device
        device_ip = self._find_or_discover_device(request.ip)
        
        if not device_ip:
            return BrowseDeviceResponse.device_not_found()
        
        # Build URL
        url = f"http://{device_ip}:{request.port}"
        
        # Open in browser if requested
        if request.open_in_browser:
            webbrowser.open(url)
        
        return BrowseDeviceResponse.success_opened(url, device_ip)
    
    def _find_or_discover_device(self, requested_ip: Optional[str]) -> Optional[str]:
        """Find device from repository or discover on network."""
        # If IP was provided, use it directly
        if requested_ip:
            return requested_ip
        
        # Try to find in repository first
        connection = DeviceConnection.for_discovery()
        stored_device = self._device_repository.find_by_connection(connection)
        
        if stored_device:
            return stored_device.connection.ip_address.value
        
        # Discover on network
        discovered_ip = self._discovery_service.discover_device()
        
        if discovered_ip:
            # Store for future use
            from ...domain.device_management.entities.device import Device
            device = Device.discover(discovered_ip, str(connection.port.value))
            self._device_repository.save(device)
            return discovered_ip
        
        return None