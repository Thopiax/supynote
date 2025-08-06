"""Device aggregate root."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from ...shared.base_entity import AggregateRoot, DomainEvent
from ..value_objects.device_connection import DeviceConnection, IPAddress, Port


class DeviceStatus(object):
    """Device status value object."""
    
    def __init__(self, is_online: bool, last_seen: Optional[datetime] = None):
        self.is_online = is_online
        self.last_seen = last_seen or datetime.now()


class DeviceCapabilities(object):
    """Device capabilities value object."""
    
    def __init__(
        self,
        supports_async: bool = True,
        max_concurrent_downloads: int = 30,
        supports_ocr: bool = True
    ):
        self.supports_async = supports_async
        self.max_concurrent_downloads = max_concurrent_downloads
        self.supports_ocr = supports_ocr


# Domain Events
class DeviceDiscovered(DomainEvent):
    """Event raised when a device is discovered."""
    def __init__(self, device_id: UUID, connection: DeviceConnection):
        super().__init__()
        self.device_id = device_id
        self.connection = connection


class DeviceConnected(DomainEvent):
    """Event raised when a device is connected."""
    def __init__(self, device_id: UUID):
        super().__init__()
        self.device_id = device_id


class DeviceDisconnected(DomainEvent):
    """Event raised when a device is disconnected."""
    def __init__(self, device_id: UUID):
        super().__init__()
        self.device_id = device_id


class Device(AggregateRoot):
    """Device aggregate root representing a Supernote device."""
    
    def __init__(
        self,
        device_id: UUID,
        connection: DeviceConnection,
        name: Optional[str] = None,
        capabilities: Optional[DeviceCapabilities] = None
    ):
        super().__init__(device_id)
        self._connection = connection
        self._name = name or f"Supernote_{connection.ip_address}"
        self._capabilities = capabilities or DeviceCapabilities()
        self._status = DeviceStatus(is_online=False)
        self._discovered_at = datetime.now()
        
        self._raise_event(DeviceDiscovered(device_id, connection))
    
    @classmethod
    def discover(cls, ip: str, port: str = "8089") -> 'Device':
        """Factory method to create a device from discovery."""
        connection = DeviceConnection.from_strings(ip, port)
        device_id = UUID(int=hash(str(connection)) % (2**128))  # Deterministic ID from connection
        return cls(device_id, connection)
    
    @property
    def connection(self) -> DeviceConnection:
        """Get the device connection info."""
        return self._connection
    
    @property
    def name(self) -> str:
        """Get the device name."""
        return self._name
    
    @property
    def capabilities(self) -> DeviceCapabilities:
        """Get device capabilities."""
        return self._capabilities
    
    @property
    def status(self) -> DeviceStatus:
        """Get current device status."""
        return self._status
    
    @property
    def is_online(self) -> bool:
        """Check if device is online."""
        return self._status.is_online
    
    @property
    def url(self) -> str:
        """Get the device URL."""
        return self._connection.url
    
    def connect(self) -> None:
        """Mark device as connected."""
        if self._status.is_online:
            return  # Already connected
        
        self._status = DeviceStatus(is_online=True)
        self._raise_event(DeviceConnected(self.id))
    
    def disconnect(self) -> None:
        """Mark device as disconnected."""
        if not self._status.is_online:
            return  # Already disconnected
        
        self._status = DeviceStatus(is_online=False)
        self._raise_event(DeviceDisconnected(self.id))
    
    def update_connection(self, new_connection: DeviceConnection) -> None:
        """Update device connection info (e.g., after network change)."""
        if self._connection != new_connection:
            self._connection = new_connection
            # Could raise a DeviceConnectionChanged event if needed
    
    def supports_feature(self, feature: str) -> bool:
        """Check if device supports a specific feature."""
        feature_map = {
            'async': self._capabilities.supports_async,
            'ocr': self._capabilities.supports_ocr,
        }
        return feature_map.get(feature, False)
    
    def get_max_workers(self, task_type: str = 'download') -> int:
        """Get the maximum number of workers for a task type."""
        if task_type == 'download':
            return self._capabilities.max_concurrent_downloads
        else:
            # Default for other tasks
            return 4
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Device(id={self.id}, name={self._name}, connection={self._connection}, online={self.is_online})"