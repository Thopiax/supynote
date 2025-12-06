"""Dependency injection container for the application."""

from ...infrastructure.repositories.memory_device_repository import InMemoryDeviceRepository
from ...infrastructure.network.network_discovery_service import NetworkDiscoveryService
from ...application.use_cases.find_device import FindDeviceUseCase
from ...application.use_cases.browse_device import BrowseDeviceUseCase
from ...application.use_cases.get_device_info import GetDeviceInfoUseCase
from ...application.use_cases.list_files import ListFilesUseCase
from ...application.use_cases.download_use_case import DownloadUseCase
from .commands.find_command import FindCommand
from .commands.browse_command import BrowseCommand
from .commands.info_command import InfoCommand
from .commands.list_command import ListCommand
from .commands.commands import (
    DownloadCommand,
    ConvertCommand,
    ValidateCommand,
    OcrCommand,
    MergeCommand
)


class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        # Infrastructure
        self._device_repository = InMemoryDeviceRepository()
        self._discovery_service = NetworkDiscoveryService()
        
        # Application
        self._find_device_use_case = FindDeviceUseCase(
            device_repository=self._device_repository,
            discovery_service=self._discovery_service
        )
        
        self._browse_device_use_case = BrowseDeviceUseCase(
            device_repository=self._device_repository,
            discovery_service=self._discovery_service
        )
        
        self._get_device_info_use_case = GetDeviceInfoUseCase(
            device_repository=self._device_repository,
            discovery_service=self._discovery_service
        )
        
        self._list_files_use_case = ListFilesUseCase(
            device_repository=self._device_repository,
            discovery_service=self._discovery_service
        )
        
        # Use case for download and related operations
        self._download_use_case = DownloadUseCase(
            device_repository=self._device_repository,
            discovery_service=self._discovery_service
        )
        
        # Presentation
        self._find_command = FindCommand(self._find_device_use_case)
        self._browse_command = BrowseCommand(self._browse_device_use_case)
        self._info_command = InfoCommand(self._get_device_info_use_case)
        self._list_command = ListCommand(self._list_files_use_case)
        
        # Command handlers
        self._download_command = DownloadCommand(self._download_use_case)
        self._convert_command = ConvertCommand(self._download_use_case)
        self._validate_command = ValidateCommand(self._download_use_case)
        self._ocr_command = OcrCommand(self._download_use_case)
        self._merge_command = MergeCommand(self._download_use_case)
    
    @property
    def find_command(self) -> FindCommand:
        """Get the find command handler."""
        return self._find_command
    
    @property
    def browse_command(self) -> BrowseCommand:
        """Get the browse command handler."""
        return self._browse_command
    
    @property
    def info_command(self) -> InfoCommand:
        """Get the info command handler."""
        return self._info_command
    
    @property
    def list_command(self) -> ListCommand:
        """Get the list command handler."""
        return self._list_command
    
    @property
    def download_command(self) -> DownloadCommand:
        """Get the download command handler."""
        return self._download_command
    
    @property
    def convert_command(self) -> ConvertCommand:
        """Get the convert command handler."""
        return self._convert_command
    
    @property
    def validate_command(self) -> ValidateCommand:
        """Get the validate command handler."""
        return self._validate_command
    
    @property
    def ocr_command(self) -> OcrCommand:
        """Get the OCR command handler."""
        return self._ocr_command

    @property
    def merge_command(self) -> MergeCommand:
        """Get the merge command handler."""
        return self._merge_command