"""Command handler for the browse command."""
from argparse import Namespace

from ....application.use_cases.browse_device import BrowseDeviceUseCase
from ....application.dtos.browse_dto import BrowseDeviceRequest


class BrowseCommand:
    """Handles the browse command in the CLI."""
    
    def __init__(self, use_case: BrowseDeviceUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """
        Execute the browse command.
        
        Args:
            args: Parsed command line arguments
        """
        # Build request from CLI arguments
        request = BrowseDeviceRequest(
            ip=args.ip,
            port=args.port,
            open_in_browser=True  # Always open for browse command
        )
        
        # Execute use case
        response = self._use_case.execute(request)
        
        # Display result
        print(response.message)