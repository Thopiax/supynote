"""Command handlers for commands using legacy adapter."""
from argparse import Namespace

from ....application.use_cases.legacy_adapter import LegacyCommandAdapter


class DownloadCommand:
    """Handles the download command using legacy adapter."""
    
    def __init__(self, adapter: LegacyCommandAdapter):
        """Initialize the command handler."""
        self._adapter = adapter
    
    def execute(self, args: Namespace) -> None:
        """Execute the download command."""
        self._adapter.execute_download(args)


class ConvertCommand:
    """Handles the convert command using legacy adapter."""
    
    def __init__(self, adapter: LegacyCommandAdapter):
        """Initialize the command handler."""
        self._adapter = adapter
    
    def execute(self, args: Namespace) -> None:
        """Execute the convert command."""
        self._adapter.execute_convert(args)


class ValidateCommand:
    """Handles the validate command using legacy adapter."""
    
    def __init__(self, adapter: LegacyCommandAdapter):
        """Initialize the command handler."""
        self._adapter = adapter
    
    def execute(self, args: Namespace) -> None:
        """Execute the validate command."""
        self._adapter.execute_validate(args)


class OcrCommand:
    """Handles the OCR command using legacy adapter."""
    
    def __init__(self, adapter: LegacyCommandAdapter):
        """Initialize the command handler."""
        self._adapter = adapter
    
    def execute(self, args: Namespace) -> None:
        """Execute the OCR command."""
        self._adapter.execute_ocr(args)