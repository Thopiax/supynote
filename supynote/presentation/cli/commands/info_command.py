"""Command handler for the info command."""
from argparse import Namespace

from ....application.use_cases.get_device_info import GetDeviceInfoUseCase
from ....application.dtos.device_info_dto import DeviceInfoRequest


class InfoCommand:
    """Handles the info command in the CLI."""
    
    def __init__(self, use_case: GetDeviceInfoUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """
        Execute the info command.
        
        Args:
            args: Parsed command line arguments
        """
        # Build request from CLI arguments
        request = DeviceInfoRequest(
            ip=args.ip,
            port=args.port,
            output_directory=args.output
        )
        
        # Execute use case
        response = self._use_case.execute(request)
        
        # Display result
        if response.success:
            print(f"\n📱 Supernote Device Info:")
            print(f"  IP: {response.ip}")
            print(f"  Port: {response.port}")
            print(f"  URL: {response.url}")
            print(f"  Status: {response.status}")
            if response.output_directory:
                print(f"  Local directory: {response.output_directory}")
        else:
            print(response.message)