"""Find device use case."""

from typing import Optional
import webbrowser

from ..dtos.device_dto import FindDeviceRequest, FindDeviceResponse
from ...domain.device_management.repositories.device_repository import (
    DeviceRepository, 
    DeviceDiscoveryService
)
from ...domain.device_management.entities.device import Device


class FindDeviceUseCase:
    """Use case for finding a Supernote device on the network."""
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        discovery_service: DeviceDiscoveryService
    ):
        self._device_repository = device_repository
        self._discovery_service = discovery_service
    
    def execute(self, request: FindDeviceRequest) -> FindDeviceResponse:
        """
        Find a Supernote device on the network.
        
        1. If IP is provided, use it directly
        2. Otherwise check if we have any known devices
        3. If not, scan the network
        4. Create and save the device if found
        5. Optionally open in browser
        """
        # If IP is provided explicitly, use it
        if request.ip:
            device = Device.discover(ip=request.ip, port="8089")
            device.connect()
            self._device_repository.save(device)
            
            if request.open_in_browser:
                webbrowser.open(device.url)
            
            return FindDeviceResponse.success(
                ip=request.ip,
                port="8089",
                url=device.url,
                name=device.name,
                source="provided"
            )
        
        # Check if we have any saved devices
        known_devices = self._device_repository.find_all()
        
        for device in known_devices:
            # Check if device is still available
            if self._discovery_service.is_device_available(device.connection):
                device.connect()
                self._device_repository.save(device)
                
                if request.open_in_browser:
                    webbrowser.open(device.url)
                
                return FindDeviceResponse.success(
                    ip=str(device.connection.ip_address),
                    port=str(device.connection.port),
                    url=device.url,
                    name=device.name,
                    source="stored"
                )
        
        # No known devices available, scan the network
        print("🔍 Scanning network for Supernote devices...")
        connections = self._discovery_service.scan_network(request.network_range)
        
        if not connections:
            return FindDeviceResponse.not_found()
        
        # Use the first connection found
        connection = connections[0]
        
        # Create new device
        device = Device.discover(
            ip=str(connection.ip_address),
            port=str(connection.port)
        )
        device.connect()
        
        # Save the device for future use
        self._device_repository.save(device)
        
        if request.open_in_browser:
            webbrowser.open(device.url)
        
        return FindDeviceResponse.success(
            ip=str(connection.ip_address),
            port=str(connection.port),
            url=device.url,
            name=device.name,
            source="network"
        )