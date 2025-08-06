"""Find command handler - presentation layer."""

from argparse import Namespace

from ....application.use_cases.find_device import FindDeviceUseCase
from ....application.dtos.device_dto import FindDeviceRequest


class FindCommand:
    """Handler for the 'find' CLI command."""
    
    def __init__(self, find_device_use_case: FindDeviceUseCase):
        self._use_case = find_device_use_case
    
    def execute(self, args: Namespace) -> None:
        """
        Execute the find command.
        
        This is a thin controller that:
        1. Maps CLI arguments to application DTOs
        2. Calls the use case
        3. Formats the output
        """
        # Map CLI args to DTO
        request = FindDeviceRequest(
            ip=getattr(args, 'ip', None),  # Get IP if provided
            network_range=None,  # Could be added as CLI option
            open_in_browser=getattr(args, 'open', False)
        )
        
        # Execute use case
        response = self._use_case.execute(request)
        
        # Format output
        if response.found:
            if response.source == "provided":
                print(f"✅ Using provided IP: {response.ip}")
            elif response.source == "stored":
                print(f"✅ Found stored Supernote device at {response.ip}")
            else:
                print(f"✅ Found Supernote device at {response.ip}")
            
            if request.open_in_browser:
                print(f"🌐 Opening {response.url} in browser...")
        else:
            print("❌ No Supernote device found on network")
            print("💡 Make sure your device is:")
            print("   - Powered on")
            print("   - Connected to the same network")
            print("   - Has sharing enabled")