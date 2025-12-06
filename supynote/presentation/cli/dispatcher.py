"""Command dispatcher for DDD commands."""
from argparse import Namespace
from typing import Optional

from .container import DIContainer


class CommandDispatcher:
    """Dispatches commands to DDD handlers when available."""
    
    # All commands now handled through DDD architecture
    DDD_COMMANDS = {
        'find', 'browse', 'info', 'list',
        'download', 'convert', 'validate', 'ocr', 'merge'
    }
    
    def __init__(self):
        """Initialize the dispatcher with DI container."""
        self._container = DIContainer()
    
    def can_handle(self, command: str) -> bool:
        """Check if a command has been migrated to DDD."""
        return command in self.DDD_COMMANDS
    
    def dispatch(self, command: str, args: Namespace) -> bool:
        """
        Dispatch a command to its DDD handler.
        
        Returns:
            True if handled, False if not a DDD command
        """
        if not self.can_handle(command):
            return False
        
        # Route to appropriate command handler
        command_map = {
            'find': self._container.find_command,
            'browse': self._container.browse_command,
            'info': self._container.info_command,
            'list': self._container.list_command,
            'download': self._container.download_command,
            'convert': self._container.convert_command,
            'validate': self._container.validate_command,
            'ocr': self._container.ocr_command,
            'merge': self._container.merge_command
        }
        
        handler = command_map.get(command)
        if handler:
            handler.execute(args)
        
        return True
    
    @classmethod
    def try_dispatch(cls, command: str, args: Namespace) -> bool:
        """
        Try to dispatch a command through DDD architecture.
        
        This is a convenience method that creates a dispatcher and attempts dispatch.
        Returns True if handled, False otherwise.
        """
        try:
            dispatcher = cls()
            return dispatcher.dispatch(command, args)
        except Exception as e:
            # If DDD fails for any reason, fall back to legacy
            print(f"⚠️ DDD dispatch failed: {e}")
            return False