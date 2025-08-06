"""Command handler for the list command."""
from argparse import Namespace

from ....application.use_cases.list_files import ListFilesUseCase
from ....application.dtos.list_files_dto import ListFilesRequest


class ListCommand:
    """Handles the list command in the CLI."""
    
    def __init__(self, use_case: ListFilesUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """
        Execute the list command.
        
        Args:
            args: Parsed command line arguments
        """
        # Build request from CLI arguments
        request = ListFilesRequest(
            ip=getattr(args, 'ip', None),
            port=getattr(args, 'port', '8089'),
            directory=getattr(args, 'directory', '')
        )
        
        # Execute use case
        response = self._use_case.execute(request)
        
        # Display result
        if response.success:
            print(f"\n📁 Files in {response.directory}:")
            for item in response.files:
                icon = "📁" if item.is_directory else "📄"
                name = item.name
                date = item.date or ""
                print(f"  {icon} {name} {date}")
        else:
            print(response.message)