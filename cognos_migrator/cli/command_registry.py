"""
Command Registry for CLI

Manages command registration and execution.
Follows Interface Segregation Principle.
"""

from typing import Dict, Callable, Any
from abc import ABC, abstractmethod


class CommandHandler(ABC):
    """Abstract base class for command handlers"""
    
    @abstractmethod
    def execute(self, args: Any) -> bool:
        """Execute the command"""
        pass


class CommandRegistry:
    """Registry for CLI commands"""
    
    def __init__(self):
        self._commands: Dict[str, CommandHandler] = {}
        self._command_map: Dict[str, str] = {
            'test-connection': 'test_connection',
            'migrate-module': 'migrate_module',
            'migrate-report': 'migrate_report',
            'post-process': 'post_process',
            'dashboard': 'dashboard',
            'batch-migrate': 'batch_migrate',
            'validate-module': 'validate_module',
            'list-strategies': 'list_strategies',
            'show-validation-config': 'show_config'
        }
    
    def register_command(self, command_name: str, handler: CommandHandler):
        """Register a command handler"""
        self._commands[command_name] = handler
    
    def get_command_handler(self, command_name: str) -> CommandHandler:
        """Get command handler by name"""
        mapped_name = self._command_map.get(command_name, command_name)
        return self._commands.get(mapped_name)
    
    def has_command(self, command_name: str) -> bool:
        """Check if command exists"""
        mapped_name = self._command_map.get(command_name, command_name)
        return mapped_name in self._commands
    
    def list_commands(self) -> list:
        """List all registered commands"""
        return list(self._command_map.keys())
    
    def execute_command(self, command_name: str, args: Any) -> bool:
        """Execute a command"""
        handler = self.get_command_handler(command_name)
        if handler:
            return handler.execute(args)
        return False