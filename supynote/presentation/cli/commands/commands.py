"""Command handlers for application use cases."""
from argparse import Namespace

from ....application.use_cases.download_use_case import DownloadUseCase


class DownloadCommand:
    """Handles the download command."""
    
    def __init__(self, use_case: DownloadUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """Execute the download command."""
        self._use_case.execute_download(args)


class ConvertCommand:
    """Handles the convert command."""
    
    def __init__(self, use_case: DownloadUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """Execute the convert command."""
        self._use_case.execute_convert(args)


class ValidateCommand:
    """Handles the validate command."""
    
    def __init__(self, use_case: DownloadUseCase):
        """Initialize the command handler."""
        self._use_case = use_case
    
    def execute(self, args: Namespace) -> None:
        """Execute the validate command."""
        self._use_case.execute_validate(args)


class OcrCommand:
    """Handles the OCR command."""

    def __init__(self, use_case: DownloadUseCase):
        """Initialize the command handler."""
        self._use_case = use_case

    def execute(self, args: Namespace) -> None:
        """Execute the OCR command."""
        self._use_case.execute_ocr(args)


class MergeCommand:
    """Handles the merge command."""

    def __init__(self, use_case: DownloadUseCase):
        """Initialize the command handler."""
        self._use_case = use_case

    def execute(self, args: Namespace) -> None:
        """Execute the merge command."""
        self._use_case.execute_merge(args)