"""In-memory implementation of device repository for now."""

from typing import Dict, List, Optional
from uuid import UUID

from ...domain.device_management.entities.device import Device
from ...domain.device_management.repositories.device_repository import DeviceRepository
from ...domain.device_management.value_objects.device_connection import DeviceConnection


class InMemoryDeviceRepository(DeviceRepository):
    """In-memory implementation of DeviceRepository."""
    
    def __init__(self):
        self._devices: Dict[UUID, Device] = {}
    
    def find_by_id(self, device_id: UUID) -> Optional[Device]:
        """Find a device by its ID."""
        return self._devices.get(device_id)
    
    def find_by_connection(self, connection: DeviceConnection) -> Optional[Device]:
        """Find a device by its connection info."""
        for device in self._devices.values():
            if device.connection == connection:
                return device
        return None
    
    def find_all(self) -> List[Device]:
        """Get all known devices."""
        return list(self._devices.values())
    
    def save(self, device: Device) -> None:
        """Save a device (create or update)."""
        self._devices[device.id] = device
        device.increment_version()
    
    def delete(self, device_id: UUID) -> None:
        """Delete a device."""
        self._devices.pop(device_id, None)