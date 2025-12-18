"""Unit tests for application use cases."""
import unittest
from unittest.mock import Mock, MagicMock, patch

from supynote.application.use_cases.find_device import FindDeviceUseCase
from supynote.application.use_cases.browse_device import BrowseDeviceUseCase
from supynote.application.use_cases.get_device_info import GetDeviceInfoUseCase
from supynote.application.dtos.device_dto import FindDeviceRequest
from supynote.application.dtos.browse_dto import BrowseDeviceRequest
from supynote.application.dtos.device_info_dto import DeviceInfoRequest
from supynote.domain.device_management.entities.device import Device


class TestFindDeviceUseCase(unittest.TestCase):
    """Test the FindDevice use case."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.mock_discovery = Mock()
        self.use_case = FindDeviceUseCase(self.mock_repo, self.mock_discovery)
    
    def test_find_with_provided_ip(self):
        """Test finding device with explicitly provided IP."""
        # Arrange
        request = FindDeviceRequest(ip="192.168.1.100", open_in_browser=False)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.found)
        self.assertEqual(response.ip, "192.168.1.100")
        self.assertEqual(response.source, "provided")
        self.mock_discovery.discover_device.assert_not_called()
    
    def test_find_with_discovery(self):
        """Test finding device through network discovery."""
        # Arrange
        from supynote.domain.device_management.value_objects.device_connection import DeviceConnection
        mock_connection = DeviceConnection.from_strings("192.168.1.42", "8089")

        self.mock_repo.find_all.return_value = []
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.scan_network.return_value = [mock_connection]
        request = FindDeviceRequest(open_in_browser=False)

        # Act
        response = self.use_case.execute(request)

        # Assert
        self.assertTrue(response.found)
        self.assertEqual(response.ip, "192.168.1.42")
        self.assertEqual(response.source, "network")
        self.mock_discovery.scan_network.assert_called_once()
        self.mock_repo.save.assert_called_once()
    
    def test_find_no_device(self):
        """Test when no device is found."""
        # Arrange
        self.mock_repo.find_all.return_value = []
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.scan_network.return_value = []
        request = FindDeviceRequest(open_in_browser=False)

        # Act
        response = self.use_case.execute(request)

        # Assert
        self.assertFalse(response.found)
        self.assertIsNone(response.ip)
        self.mock_discovery.scan_network.assert_called_once()


class TestBrowseDeviceUseCase(unittest.TestCase):
    """Test the BrowseDevice use case."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.mock_discovery = Mock()
        self.use_case = BrowseDeviceUseCase(self.mock_repo, self.mock_discovery)
    
    @patch('webbrowser.open')
    def test_browse_with_provided_ip(self, mock_browser):
        """Test browsing with provided IP."""
        # Arrange
        request = BrowseDeviceRequest(ip="192.168.1.100", port="8089")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.url, "http://192.168.1.100:8089")
        self.assertEqual(response.device_ip, "192.168.1.100")
        mock_browser.assert_called_once_with("http://192.168.1.100:8089")
    
    @patch('webbrowser.open')
    def test_browse_with_discovery(self, mock_browser):
        """Test browsing with device discovery."""
        # Arrange
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.discover_device.return_value = "192.168.1.42"
        request = BrowseDeviceRequest(port="8089")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.url, "http://192.168.1.42:8089")
        mock_browser.assert_called_once_with("http://192.168.1.42:8089")
    
    def test_browse_no_device(self):
        """Test browsing when no device is found."""
        # Arrange
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.discover_device.return_value = None
        request = BrowseDeviceRequest()
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertIsNone(response.url)


class TestGetDeviceInfoUseCase(unittest.TestCase):
    """Test the GetDeviceInfo use case."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.mock_discovery = Mock()
        self.use_case = GetDeviceInfoUseCase(self.mock_repo, self.mock_discovery)
    
    def test_info_with_provided_ip(self):
        """Test getting info with provided IP."""
        # Arrange
        request = DeviceInfoRequest(ip="192.168.1.100", port="8089")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.ip, "192.168.1.100")
        self.assertEqual(response.port, "8089")
        self.assertEqual(response.url, "http://192.168.1.100:8089")
        self.assertEqual(response.status, "🟢 Connected")
    
    def test_info_with_discovery(self):
        """Test getting info through discovery."""
        # Arrange
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.discover_device.return_value = "192.168.1.42"
        request = DeviceInfoRequest(port="8089", output_directory="/tmp/test")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.ip, "192.168.1.42")
        self.assertIsNotNone(response.output_directory)
        self.assertIn("/tmp/test", response.output_directory)
    
    def test_info_no_device(self):
        """Test getting info when no device is found."""
        # Arrange
        self.mock_repo.find_by_connection.return_value = None
        self.mock_discovery.discover_device.return_value = None
        request = DeviceInfoRequest()
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertIsNone(response.ip)


if __name__ == "__main__":
    unittest.main()