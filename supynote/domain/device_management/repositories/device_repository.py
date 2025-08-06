"""Device repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.device import Device
from ..value_objects.device_connection import DeviceConnection


class DeviceRepository(ABC):
    """Repository interface for Device aggregate."""
    
    @abstractmethod
    def find_by_id(self, device_id: UUID) -> Optional[Device]:
        """Find a device by its ID."""
        pass
    
    @abstractmethod
    def find_by_connection(self, connection: DeviceConnection) -> Optional[Device]:
        """Find a device by its connection info."""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Device]:
        """Get all known devices."""
        pass
    
    @abstractmethod
    def save(self, device: Device) -> None:
        """Save a device (create or update)."""
        pass
    
    @abstractmethod
    def delete(self, device_id: UUID) -> None:
        """Delete a device."""
        pass


class DeviceDiscoveryService(ABC):
    """Service interface for device discovery."""
    
    @abstractmethod
    def scan_network(self, network_range: Optional[str] = None) -> List[DeviceConnection]:
        """Scan network for Supernote devices."""
        pass
    
    @abstractmethod
    def is_device_available(self, connection: DeviceConnection) -> bool:
        """Check if a device is available at the given connection."""
        pass