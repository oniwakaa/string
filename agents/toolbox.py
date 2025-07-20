"""
Secure Toolbox Module for AI-Powered Coding Assistant

This module provides a centralized, secure, and auditable API for all local 
system interactions including file system operations and shell command execution.

Security Features:
- Path validation and sanitization
- Command whitelist filtering  
- Comprehensive logging and auditing
- Error handling and rollback capabilities
- Resource limits and timeouts

Author: Claude Code Assistant
Date: 2024-12-19
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import json
import hashlib
import tempfile


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class ToolboxConfig:
    """Configuration class for security settings and limits."""
    
    # Path security settings
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.scss',
        '.json', '.yaml', '.yml', '.md', '.txt', '.csv', '.xml',
        '.sql', '.sh', '.bat', '.env', '.gitignore', '.dockerfile'
    }
    
    BLOCKED_PATHS = {
        '/etc', '/usr', '/bin', '/sbin', '/var', '/root', '/home',
        'C:\\Windows', 'C:\\Program Files', 'C:\\Users'
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_COMMAND_TIMEOUT = 30  # seconds
    
    # Command whitelist - only safe, non-destructive commands
    ALLOWED_COMMANDS = {
        'git', 'npm', 'yarn', 'pip', 'poetry', 'pytest', 'python',
        'node', 'tsc', 'eslint', 'prettier', 'black', 'flake8',
        'cargo', 'rustc', 'go', 'javac', 'java', 'mvn', 'gradle'
    }
    
    BLOCKED_COMMANDS = {
        'rm', 'del', 'format', 'fdisk', 'dd', 'mkfs', 'sudo', 'su',
        'chmod', 'chown', 'passwd', 'userdel', 'useradd', 'shutdown',
        'reboot', 'halt', 'poweroff', 'systemctl', 'service'
    }


class SecureToolbox:
    """
    Secure toolbox for file system and shell operations.
    
    This class provides a centralized API for all local system interactions
    with comprehensive security measures, logging, and audit trails.
    """
    
    def __init__(self, project_root: Optional[str] = None, log_file: Optional[str] = None):
        """
        Initialize the secure toolbox.
        
        Args:
            project_root: Root directory for file operations (defaults to current working directory)
            log_file: Path to log file for audit trail (defaults to toolbox.log)
        """
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.log_file = log_file or "toolbox.log"
        
        # Setup logging
        self._setup_logging()
        
        # Security validation
        self._validate_project_root()
        
        self.logger.info(f"SecureToolbox initialized with project_root: {self.project_root}")
    
    def _setup_logging(self):
        """Setup comprehensive logging for audit trail."""
        self.logger = logging.getLogger('SecureToolbox')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _validate_project_root(self):
        """Validate that the project root is safe for operations."""
        if not self.project_root.exists():
            raise SecurityError(f"Project root does not exist: {self.project_root}")
        
        if not self.project_root.is_dir():
            raise SecurityError(f"Project root is not a directory: {self.project_root}")
        
        # Check if project root is in blocked paths
        for blocked_path in ToolboxConfig.BLOCKED_PATHS:
            if str(self.project_root).startswith(blocked_path):
                raise SecurityError(f"Project root is in blocked path: {self.project_root}")
        
        self.logger.info(f"Project root validation passed: {self.project_root}")
    
    def _validate_path(self, file_path: Union[str, Path]) -> Path:
        """
        Validate and sanitize file paths for security.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Resolved and validated Path object
            
        Raises:
            SecurityError: If path is invalid or unsafe
        """
        try:
            # Convert to Path object and resolve
            path = Path(file_path).resolve()
            
            # Check if path is within project root
            try:
                path.relative_to(self.project_root)
            except ValueError:
                raise SecurityError(f"Path is outside project root: {path}")
            
            # Check file extension if it's a file
            if path.suffix and path.suffix.lower() not in ToolboxConfig.ALLOWED_EXTENSIONS:
                raise SecurityError(f"File extension not allowed: {path.suffix}")
            
            # Check for blocked path components
            for blocked_path in ToolboxConfig.BLOCKED_PATHS:
                if str(path).startswith(blocked_path):
                    raise SecurityError(f"Path contains blocked component: {path}")
            
            # Check for suspicious patterns
            suspicious_patterns = ['..', '~', '$', '`', ';', '&', '|']
            for pattern in suspicious_patterns:
                if pattern in str(path):
                    raise SecurityError(f"Path contains suspicious pattern '{pattern}': {path}")
            
            return path
            
        except Exception as e:
            if isinstance(e, SecurityError):
                raise
            raise SecurityError(f"Path validation failed: {str(e)}")
    
    def _validate_command(self, command: List[str]) -> bool:
        """
        Validate that a command is safe to execute.
        
        Args:
            command: Command as list of strings
            
        Returns:
            True if command is safe
            
        Raises:
            SecurityError: If command is blocked or unsafe
        """
        if not command:
            raise SecurityError("Empty command not allowed")
        
        base_command = command[0].split('/')[-1]  # Extract command name
        
        # Check if command is explicitly blocked
        if base_command in ToolboxConfig.BLOCKED_COMMANDS:
            raise SecurityError(f"Command is blocked: {base_command}")
        
        # Check if command is in whitelist
        if base_command not in ToolboxConfig.ALLOWED_COMMANDS:
            raise SecurityError(f"Command not in whitelist: {base_command}")
        
        # Check for suspicious patterns in arguments
        suspicious_patterns = ['rm -rf', 'sudo', '&&', '||', ';', '`', '$(' ]
        command_str = ' '.join(command)
        for pattern in suspicious_patterns:
            if pattern in command_str:
                raise SecurityError(f"Command contains suspicious pattern '{pattern}': {command_str}")
        
        return True
    
    def _log_operation(self, operation: str, target: str, success: bool, details: str = ""):
        """Log an operation for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'target': target,
            'success': success,
            'details': details,
            'project_root': str(self.project_root)
        }
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"{operation} - {target} - {'SUCCESS' if success else 'FAILED'} - {details}")
        
        return log_entry

    def create_file(self, file_path: str, content: str, backup: bool = True) -> Dict[str, any]:
        """
        Create a new file with security validation.
        
        Args:
            file_path: Path where to create the file
            content: Content to write to the file
            backup: Whether to create backup if file exists
            
        Returns:
            Dictionary with operation result and metadata
        """
        operation_start = datetime.now()
        
        try:
            # Validate path
            validated_path = self._validate_path(file_path)
            
            # Check if file already exists
            if validated_path.exists():
                if backup:
                    backup_path = validated_path.with_suffix(validated_path.suffix + '.backup')
                    shutil.copy2(validated_path, backup_path)
                    self.logger.info(f"Created backup: {backup_path}")
                else:
                    raise SecurityError(f"File already exists and backup=False: {validated_path}")
            
            # Validate content size
            if len(content.encode('utf-8')) > ToolboxConfig.MAX_FILE_SIZE:
                raise SecurityError(f"Content size exceeds limit: {len(content)} bytes")
            
            # Create parent directories if they don't exist
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Calculate file hash for integrity
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Log successful operation
            self._log_operation(
                operation="CREATE_FILE",
                target=str(validated_path),
                success=True,
                details=f"Size: {len(content)} bytes, Hash: {file_hash[:16]}..."
            )
            
            return {
                'success': True,
                'path': str(validated_path),
                'size': len(content),
                'hash': file_hash,
                'execution_time': (datetime.now() - operation_start).total_seconds(),
                'backup_created': backup and validated_path.exists()
            }
            
        except Exception as e:
            # Log failed operation
            self._log_operation(
                operation="CREATE_FILE",
                target=file_path,
                success=False,
                details=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'execution_time': (datetime.now() - operation_start).total_seconds()
            }

    def edit_file(self, file_path: str, content: str, create_backup: bool = True) -> Dict[str, any]:
        """
        Edit an existing file with backup and validation.
        
        Args:
            file_path: Path to the file to edit
            content: New content for the file
            create_backup: Whether to create backup before editing
            
        Returns:
            Dictionary with operation result and metadata
        """
        operation_start = datetime.now()
        backup_path = None
        
        try:
            # Validate path
            validated_path = self._validate_path(file_path)
            
            # Check if file exists
            if not validated_path.exists():
                raise SecurityError(f"File does not exist: {validated_path}")
            
            # Validate content size
            if len(content.encode('utf-8')) > ToolboxConfig.MAX_FILE_SIZE:
                raise SecurityError(f"Content size exceeds limit: {len(content)} bytes")
            
            # Create backup if requested
            original_hash = None
            if create_backup:
                # Read original content for hash
                with open(validated_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                original_hash = hashlib.sha256(original_content.encode('utf-8')).hexdigest()
                
                # Create backup
                backup_path = validated_path.with_suffix(validated_path.suffix + '.backup')
                shutil.copy2(validated_path, backup_path)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Write new content
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Calculate new file hash
            new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Log successful operation
            self._log_operation(
                operation="EDIT_FILE",
                target=str(validated_path),
                success=True,
                details=f"Size: {len(content)} bytes, New Hash: {new_hash[:16]}..."
            )
            
            return {
                'success': True,
                'path': str(validated_path),
                'size': len(content),
                'original_hash': original_hash,
                'new_hash': new_hash,
                'backup_path': str(backup_path) if backup_path else None,
                'execution_time': (datetime.now() - operation_start).total_seconds()
            }
            
        except Exception as e:
            # Log failed operation
            self._log_operation(
                operation="EDIT_FILE",
                target=file_path,
                success=False,
                details=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'execution_time': (datetime.now() - operation_start).total_seconds()
            }

    def run_terminal_command(self, command: Union[str, List[str]], timeout: int = None) -> Dict[str, any]:
        """
        Execute a terminal command with security validation.
        
        Args:
            command: Command to execute (string or list)
            timeout: Timeout in seconds (defaults to MAX_COMMAND_TIMEOUT)
            
        Returns:
            Dictionary with command result and metadata
        """
        operation_start = datetime.now()
        timeout = timeout or ToolboxConfig.MAX_COMMAND_TIMEOUT
        
        try:
            # Convert command to list if string
            if isinstance(command, str):
                command_list = command.split()
            else:
                command_list = command
            
            # Validate command
            self._validate_command(command_list)
            
            # Execute command
            result = subprocess.run(
                command_list,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Log successful execution
            self._log_operation(
                operation="RUN_COMMAND",
                target=' '.join(command_list),
                success=result.returncode == 0,
                details=f"Exit code: {result.returncode}, Timeout: {timeout}s"
            )
            
            return {
                'success': result.returncode == 0,
                'command': ' '.join(command_list),
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': (datetime.now() - operation_start).total_seconds(),
                'timeout_used': timeout
            }
            
        except subprocess.TimeoutExpired as e:
            # Log timeout
            self._log_operation(
                operation="RUN_COMMAND",
                target=' '.join(command_list),
                success=False,
                details=f"Command timed out after {timeout}s"
            )
            
            return {
                'success': False,
                'error': f"Command timed out after {timeout} seconds",
                'error_type': 'TimeoutError',
                'command': ' '.join(command_list),
                'execution_time': timeout
            }
            
        except Exception as e:
            # Log failed execution
            command_str = ' '.join(command_list) if isinstance(command, list) else str(command)
            self._log_operation(
                operation="RUN_COMMAND",
                target=command_str,
                success=False,
                details=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'command': command_str,
                'execution_time': (datetime.now() - operation_start).total_seconds()
            }

    def get_security_status(self) -> Dict[str, any]:
        """
        Get current security configuration and status.
        
        Returns:
            Dictionary with security settings and status
        """
        return {
            'project_root': str(self.project_root),
            'log_file': self.log_file,
            'allowed_extensions': list(ToolboxConfig.ALLOWED_EXTENSIONS),
            'blocked_paths': list(ToolboxConfig.BLOCKED_PATHS),
            'allowed_commands': list(ToolboxConfig.ALLOWED_COMMANDS),
            'blocked_commands': list(ToolboxConfig.BLOCKED_COMMANDS),
            'max_file_size': ToolboxConfig.MAX_FILE_SIZE,
            'max_command_timeout': ToolboxConfig.MAX_COMMAND_TIMEOUT,
            'toolbox_initialized': True,
            'audit_logging_enabled': True
        }

    def get_audit_log(self, lines: int = 50) -> List[str]:
        """
        Get recent entries from the audit log.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of recent log entries
        """
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            return log_lines[-lines:] if len(log_lines) > lines else log_lines
            
        except FileNotFoundError:
            return ["Log file not found"]
        except Exception as e:
            return [f"Error reading log file: {str(e)}"]


# Convenience functions for direct usage
def create_secure_toolbox(project_root: str = None, log_file: str = None) -> SecureToolbox:
    """
    Create a new SecureToolbox instance with validation.
    
    Args:
        project_root: Root directory for operations
        log_file: Path to log file
        
    Returns:
        Configured SecureToolbox instance
    """
    return SecureToolbox(project_root=project_root, log_file=log_file)


# Example usage and testing functions
if __name__ == "__main__":
    # Example usage
    toolbox = create_secure_toolbox()
    
    print("🔒 SecureToolbox Example Usage")
    print("=" * 50)
    
    # Display security status
    status = toolbox.get_security_status()
    print(f"Project Root: {status['project_root']}")
    print(f"Max File Size: {status['max_file_size']} bytes")
    print(f"Command Timeout: {status['max_command_timeout']}s")
    
    # Example file creation
    result = toolbox.create_file(
        file_path="test_file.py",
        content="# Test file created by SecureToolbox\nprint('Hello, World!')\n"
    )
    print(f"File creation: {'✅' if result['success'] else '❌'}")
    
    # Example command execution
    cmd_result = toolbox.run_terminal_command(["python", "--version"])
    print(f"Command execution: {'✅' if cmd_result['success'] else '❌'}")
    if cmd_result['success']:
        print(f"Output: {cmd_result['stdout'].strip()}")