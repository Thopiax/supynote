"""Use case for listing files on device."""
from typing import Optional, List

from ..dtos.list_files_dto import ListFilesRequest, ListFilesResponse, FileItem
from ...domain.device_management.repositories.device_repository import DeviceRepository
from ...domain.device_management.value_objects.device_connection import DeviceConnection
from ...infrastructure.network.network_discovery_service import NetworkDiscoveryService


class ListFilesUseCase:
    """Use case for listing files on a Supernote device."""
    
    def __init__(
        self,
        device_repository: DeviceRepository,
        discovery_service: NetworkDiscoveryService
    ):
        """Initialize the use case."""
        self._device_repository = device_repository
        self._discovery_service = discovery_service
    
    def execute(self, request: ListFilesRequest) -> ListFilesResponse:
        """
        Execute the list files use case.
        
        1. Find or discover device
        2. Connect to device
        3. List files in directory
        4. Return formatted response
        """
        # Try to find device
        device_ip = self._find_or_discover_device(request.ip)
        
        if not device_ip:
            return ListFilesResponse.error(
                "❌ No Supernote device found. Use --ip to specify manually."
            )
        
        # In a real implementation, we would use a domain service
        # to actually fetch files from the device. For now, we'll
        # use the existing infrastructure directly
        try:
            from ...supernote import Supernote
            device = Supernote(device_ip, request.port)
            data = device.list_files(request.directory)
            
            if data and "fileList" in data:
                files = []
                for item in data["fileList"]:
                    files.append(FileItem(
                        name=item["name"],
                        is_directory=item["isDirectory"],
                        date=item.get("date", ""),
                        size=item.get("size"),
                        path=item.get("path")
                    ))
                
                return ListFilesResponse.success_with_files(
                    directory=request.directory,
                    files=files
                )
            else:
                return ListFilesResponse.error("❌ Could not list files")
                
        except Exception as e:
            return ListFilesResponse.error(f"❌ Error listing files: {str(e)}")
    
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