"""Network discovery service implementation."""

from typing import List, Optional
import socket
from concurrent.futures import ThreadPoolExecutor

from ...domain.device_management.repositories.device_repository import DeviceDiscoveryService
from ...domain.device_management.value_objects.device_connection import (
    DeviceConnection, 
    IPAddress, 
    Port
)


class NetworkDiscoveryService(DeviceDiscoveryService):
    """Implementation of device discovery using network scanning."""
    
    def __init__(self, default_port: int = 8089):
        self._default_port = default_port
    
    def scan_network(self, network_range: Optional[str] = None) -> List[DeviceConnection]:
        """Scan network for Supernote devices."""
        # This is a simplified version - the real implementation would use
        # the existing device_finder module
        connections = []
        
        # Import the existing device finder
        from ...device_finder import find_device
        
        ip = find_device()
        if ip:
            print(f"✅ Found Supernote device at {ip}")
            connection = DeviceConnection(
                IPAddress(ip),
                Port(self._default_port)
            )
            connections.append(connection)
        else:
            print("❌ No Supernote device found on network")
        
        return connections
    
    def discover_device(self) -> Optional[str]:
        """Discover and return the IP address of the first found device."""
        connections = self.scan_network()
        if connections:
            return str(connections[0].ip_address)
        return None
    
    def is_device_available(self, connection: DeviceConnection) -> bool:
        """Check if a device is available at the given connection."""
        try:
            # Try to connect to the device
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((str(connection.ip_address), connection.port.value))
            sock.close()
            return result == 0
        except Exception:
            return False