"""
Refactored CLI main entry point using Domain-Driven Design.

This demonstrates how the CLI would look after full refactoring.
Currently only the 'find' command is refactored as a proof of concept.
"""

import argparse
import sys
from pathlib import Path

from .container import DIContainer


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Simple CLI tool to interact with Supernote devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  supynote find                    # Find Supernote device on network
  supynote browse                  # Open device web interface
  supynote list                    # List all files on device
  supynote download Note           # Download Note directory
  supynote convert file.note       # Convert .note file to PDF
        """
    )
    
    parser.add_argument("--ip", help="Supernote device IP address")
    parser.add_argument("--port", default="8089", help="Device port (default: 8089)")
    parser.add_argument("--output", "-o", help="Local output directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Find command (refactored)
    find_parser = subparsers.add_parser("find", help="Find Supernote device on network")
    find_parser.add_argument("--open", action="store_true", help="Open device in browser")
    
    # Other commands would be added here as they are refactored
    # browse_parser = subparsers.add_parser("browse", help="Open device web interface")
    # list_parser = subparsers.add_parser("list", help="List files on device")
    # etc.
    
    return parser


def main():
    """Main entry point for the refactored CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create dependency injection container
    container = DIContainer()
    
    # Route to appropriate command handler
    if args.command == "find":
        # This is the refactored command using DDD
        container.find_command.execute(args)
    else:
        # For now, fall back to the old implementation for other commands
        print(f"⚠️ Command '{args.command}' not yet refactored")
        print("💡 Only 'find' command has been refactored as proof of concept")
        
        # In production, we would gradually refactor each command
        # and replace the old implementation with the new one


if __name__ == "__main__":
    main()