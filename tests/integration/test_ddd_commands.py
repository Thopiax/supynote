"""Integration tests for DDD-refactored commands."""
import unittest
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from supynote.presentation.cli.container import DIContainer
from supynote.application.dtos.device_dto import FindDeviceResponse
from supynote.application.dtos.browse_dto import BrowseDeviceResponse
from supynote.application.dtos.device_info_dto import DeviceInfoResponse


class TestFindCommand(unittest.TestCase):
    """Test the refactored find command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = DIContainer()
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    @patch('webbrowser.open')
    def test_find_command_with_device_found(self, mock_browser, mock_discover):
        """Test find command when device is found."""
        # Arrange
        mock_discover.return_value = "192.168.1.42"
        args = Namespace(ip=None, port="8089", open=True)
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.find_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_browser.assert_called_once_with("http://192.168.1.42:8089")
        mock_print.assert_any_call("🔍 Searching for Supernote device on network...")
        mock_print.assert_any_call("✅ Found Supernote device at 192.168.1.42")
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    def test_find_command_no_device(self, mock_discover):
        """Test find command when no device is found."""
        # Arrange
        mock_discover.return_value = None
        args = Namespace(ip=None, port="8089", open=False)
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.find_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_print.assert_any_call("❌ No Supernote device found on network")
    
    def test_find_command_with_provided_ip(self):
        """Test find command with explicitly provided IP."""
        # Arrange
        args = Namespace(ip="192.168.1.100", port="8089", open=False)
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.find_command.execute(args)
        
        # Assert
        mock_print.assert_any_call("✅ Using provided IP: 192.168.1.100")


class TestBrowseCommand(unittest.TestCase):
    """Test the refactored browse command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = DIContainer()
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    @patch('webbrowser.open')
    def test_browse_command_with_discovery(self, mock_browser, mock_discover):
        """Test browse command with device discovery."""
        # Arrange
        mock_discover.return_value = "192.168.1.42"
        args = Namespace(ip=None, port="8089")
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.browse_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_browser.assert_called_once_with("http://192.168.1.42:8089")
        mock_print.assert_called_with("🌐 Opening http://192.168.1.42:8089 in browser...")
    
    @patch('webbrowser.open')
    def test_browse_command_with_provided_ip(self, mock_browser):
        """Test browse command with provided IP."""
        # Arrange
        args = Namespace(ip="192.168.1.100", port="8089")
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.browse_command.execute(args)
        
        # Assert
        mock_browser.assert_called_once_with("http://192.168.1.100:8089")
        mock_print.assert_called_with("🌐 Opening http://192.168.1.100:8089 in browser...")
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    def test_browse_command_no_device(self, mock_discover):
        """Test browse command when no device is found."""
        # Arrange
        mock_discover.return_value = None
        args = Namespace(ip=None, port="8089")
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.browse_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_print.assert_called_with("❌ No Supernote device found. Use --ip to specify manually.")


class TestInfoCommand(unittest.TestCase):
    """Test the refactored info command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = DIContainer()
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    def test_info_command_with_discovery(self, mock_discover):
        """Test info command with device discovery."""
        # Arrange
        mock_discover.return_value = "192.168.1.42"
        args = Namespace(ip=None, port="8089", output="/tmp/supynote")
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.info_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_print.assert_any_call("\n📱 Supernote Device Info:")
        mock_print.assert_any_call("  IP: 192.168.1.42")
        mock_print.assert_any_call("  Port: 8089")
        mock_print.assert_any_call("  URL: http://192.168.1.42:8089")
        mock_print.assert_any_call("  Status: 🟢 Connected")
    
    def test_info_command_with_provided_ip(self):
        """Test info command with provided IP."""
        # Arrange
        args = Namespace(ip="192.168.1.100", port="8090", output=None)
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.info_command.execute(args)
        
        # Assert
        mock_print.assert_any_call("\n📱 Supernote Device Info:")
        mock_print.assert_any_call("  IP: 192.168.1.100")
        mock_print.assert_any_call("  Port: 8090")
        mock_print.assert_any_call("  URL: http://192.168.1.100:8090")
    
    @patch('supynote.infrastructure.network.network_discovery_service.NetworkDiscoveryService.discover_device')
    def test_info_command_no_device(self, mock_discover):
        """Test info command when no device is found."""
        # Arrange
        mock_discover.return_value = None
        args = Namespace(ip=None, port="8089", output=None)
        
        # Act
        with patch('builtins.print') as mock_print:
            self.container.info_command.execute(args)
        
        # Assert
        mock_discover.assert_called_once()
        mock_print.assert_called_with("❌ No Supernote device found. Use --ip to specify manually.")


class TestDIContainer(unittest.TestCase):
    """Test the dependency injection container."""
    
    def test_container_initialization(self):
        """Test that container initializes all services correctly."""
        container = DIContainer()
        
        # Assert all commands are available
        self.assertIsNotNone(container.find_command)
        self.assertIsNotNone(container.browse_command)
        self.assertIsNotNone(container.info_command)
    
    def test_singleton_behavior(self):
        """Test that container returns same instances."""
        container = DIContainer()
        
        # Get commands twice
        find1 = container.find_command
        find2 = container.find_command
        
        # Should be the same instance
        self.assertIs(find1, find2)


if __name__ == "__main__":
    unittest.main()