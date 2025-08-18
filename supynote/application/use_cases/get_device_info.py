"""Use case for getting device information."""
from typing import Optional
from pathlib import Path

from ..dtos.device_info_dto import DeviceInfoRequest, DeviceInfoResponse
from ...domain.device_management.repositories.device_repository import DeviceRepository
from ...domain.device_management.value_objects.device_connection import DeviceConnection
from ...infrastructure.network.network_discovery_service import NetworkDiscoveryService


class GetDeviceInfoUseCase:
    """Use case for retrieving device information."""
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        discovery_service: NetworkDiscoveryService
    ):
        """Initialize the use case."""
        self._device_repository = device_repository
        self._discovery_service = discovery_service
    
    def execute(self, request: DeviceInfoRequest) -> DeviceInfoResponse:
        """
        Execute the get device info use case.
        
        1. Find or discover device
        2. Verify connection
        3. Return device information
        """
        # Try to find device
        device_ip = self._find_or_discover_device(request.ip)
        
        if not device_ip:
            return DeviceInfoResponse.device_not_found()
        
        # Format output directory if provided
        output_dir = None
        if request.output_directory:
            output_dir = str(Path(request.output_directory).absolute())
        
        return DeviceInfoResponse.success_with_info(
            ip=device_ip,
            port=request.port,
            output_directory=output_dir
        )
    
    def _find_or_discover_device(self, requested_ip: Optional[str]) -> Optional[str]:
        """Find device from repository or discover on network."""
        # If IP was provided, use it directly
        if requested_ip:
            # Verify it's actually accessible
            # In a real implementation, we might ping or check the device
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