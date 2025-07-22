"""
Specialized Agents Module

This module contains specialized agents that perform specific, focused tasks
without requiring LLM capabilities. These agents act as secure dispatchers
and executors for various system operations.

Author: Claude Code Assistant
Date: 2024-12-19
"""

import json
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from .base import BaseAgent, Task, Result
from .toolbox import SecureToolbox, create_secure_toolbox


class ToolExecutorAgent(BaseAgent):
    """
    Tool Executor Agent - Secure, Non-LLM Dispatcher
    
    This agent acts as a secure dispatcher for toolbox functions. It makes no
    decisions and uses no LLM - it simply parses structured commands and
    executes the requested tools with the provided arguments.
    
    Key Features:
    - No LLM dependency (model_name = None)
    - Secure tool registry with predefined functions
    - JSON-based command parsing
    - Comprehensive error handling and validation
    - Complete audit trail for all operations
    """
    
    def __init__(self, project_root: Optional[str] = None, log_file: Optional[str] = None):
        """
        Initialize the ToolExecutorAgent.
        
        Args:
            project_root: Root directory for toolbox operations
            log_file: Path to log file for audit trail
        """
        super().__init__(
            name="ToolExecutorAgent",
            role="tool_executor",
            model_name=None  # No LLM required
        )
        
        # Initialize secure toolbox
        self.toolbox = create_secure_toolbox(
            project_root=project_root,
            log_file=log_file
        )
        
        # Tool registry - mapping tool names to actual functions
        self.tool_registry: Dict[str, Callable] = {
            'create_file': self.toolbox.create_file,
            'edit_file': self.toolbox.edit_file,
            'run_terminal_command': self.toolbox.run_terminal_command,
            'get_security_status': self.toolbox.get_security_status,
            'get_audit_log': self.toolbox.get_audit_log
        }
        
        # Setup logging for agent operations
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        self.logger.setLevel(logging.INFO)
        
        # Agent is ready immediately (no model loading required)
        self.status = 'ready'
        
        self.logger.info(f"ToolExecutorAgent initialized with {len(self.tool_registry)} available tools")
    
    def lazy_load_model(self):
        """
        Override lazy_load_model since this agent doesn't use any models.
        This agent is always ready.
        """
        self.status = 'ready'
        self.logger.info("ToolExecutorAgent is model-free and ready")
    
    async def execute(self, task: Task) -> Result:
        """
        Execute a tool command by parsing the task and dispatching to the appropriate tool.
        
        Expected task.prompt format:
        {
            "tool": "tool_name",
            "args": {
                "arg1": "value1",
                "arg2": "value2"
            }
        }
        
        Args:
            task: Task containing JSON-formatted tool command
            
        Returns:
            Result object with tool execution outcome
        """
        execution_start = datetime.now()
        
        try:
            # Log the incoming task
            self.logger.info(f"Executing tool task: {task.task_id}")
            
            # Parse the JSON command from task prompt
            try:
                command_data = json.loads(task.prompt)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in task prompt: {str(e)}"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            # Validate command structure
            if not isinstance(command_data, dict):
                error_msg = "Command must be a JSON object"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            # Extract tool name
            tool_name = command_data.get('tool')
            if not tool_name:
                error_msg = "Missing 'tool' field in command"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            # Extract arguments (default to empty dict if not provided)
            args = command_data.get('args', {})
            if not isinstance(args, dict):
                error_msg = "Tool arguments must be a dictionary"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            # Look up tool in registry
            if tool_name not in self.tool_registry:
                available_tools = list(self.tool_registry.keys())
                error_msg = f"Tool '{tool_name}' not found. Available tools: {available_tools}"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            # Get the tool function
            tool_function = self.tool_registry[tool_name]
            
            # Execute the tool with the provided arguments
            self.logger.info(f"Executing tool '{tool_name}' with args: {args}")
            
            try:
                # Call the tool function with unpacked arguments
                tool_result = tool_function(**args)
                
                # Calculate execution time
                execution_time = (datetime.now() - execution_start).total_seconds()
                
                # Check if tool execution was successful
                if isinstance(tool_result, dict) and 'success' in tool_result:
                    # Tool returned a structured result
                    if tool_result['success']:
                        self.logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.3f}s")
                        return Result(
                            task_id=task.task_id,
                            status="success",
                            output=tool_result
                        )
                    else:
                        # Tool reported failure
                        error_msg = tool_result.get('error', 'Tool execution failed')
                        self.logger.error(f"Tool '{tool_name}' failed: {error_msg}")
                        return Result(
                            task_id=task.task_id,
                            status="failure",
                            output="",
                            error_message=error_msg
                        )
                else:
                    # Tool returned simple result (like get_security_status)
                    self.logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.3f}s")
                    return Result(
                        task_id=task.task_id,
                        status="success",
                        output=tool_result
                    )
                    
            except TypeError as e:
                # Handle argument mismatch errors
                error_msg = f"Invalid arguments for tool '{tool_name}': {str(e)}"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
            
            except Exception as e:
                # Handle any other tool execution errors
                error_msg = f"Tool '{tool_name}' execution failed: {str(e)}"
                self.logger.error(error_msg)
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output="",
                    error_message=error_msg
                )
        
        except Exception as e:
            # Handle any unexpected errors in the execute method itself
            error_msg = f"ToolExecutorAgent execution failed: {str(e)}"
            self.logger.error(error_msg)
            return Result(
                task_id=task.task_id,
                status="failure",
                output="",
                error_message=error_msg
            )
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get information about all available tools in the registry.
        
        Returns:
            Dictionary with tool information and signatures
        """
        tools_info = {}
        
        for tool_name, tool_function in self.tool_registry.items():
            # Get function signature and docstring
            import inspect
            signature = inspect.signature(tool_function)
            docstring = inspect.getdoc(tool_function) or "No description available"
            
            tools_info[tool_name] = {
                'function': tool_name,
                'parameters': [param.name for param in signature.parameters.values()],
                'signature': str(signature),
                'description': docstring.split('\n')[0]  # First line of docstring
            }
        
        return {
            'available_tools': tools_info,
            'total_tools': len(self.tool_registry),
            'agent_status': self.status,
            'toolbox_info': self.toolbox.get_security_status()
        }
    
    def validate_command(self, command_json: str) -> Dict[str, Any]:
        """
        Validate a command without executing it.
        
        Args:
            command_json: JSON string with tool command
            
        Returns:
            Validation result with details
        """
        try:
            # Parse JSON
            command_data = json.loads(command_json)
            
            # Validate structure
            if not isinstance(command_data, dict):
                return {
                    'valid': False,
                    'error': 'Command must be a JSON object'
                }
            
            # Check for required fields
            tool_name = command_data.get('tool')
            if not tool_name:
                return {
                    'valid': False,
                    'error': 'Missing required field: tool'
                }
            
            # Check if tool exists
            if tool_name not in self.tool_registry:
                return {
                    'valid': False,
                    'error': f'Unknown tool: {tool_name}',
                    'available_tools': list(self.tool_registry.keys())
                }
            
            # Validate arguments structure
            args = command_data.get('args', {})
            if not isinstance(args, dict):
                return {
                    'valid': False,
                    'error': 'Arguments must be a dictionary'
                }
            
            # Get function signature for parameter validation
            import inspect
            tool_function = self.tool_registry[tool_name]
            signature = inspect.signature(tool_function)
            
            # Check for required parameters
            required_params = [
                param.name for param in signature.parameters.values()
                if param.default is param.empty and param.name != 'self'
            ]
            
            missing_params = [param for param in required_params if param not in args]
            if missing_params:
                return {
                    'valid': False,
                    'error': f'Missing required parameters: {missing_params}',
                    'required_parameters': required_params
                }
            
            return {
                'valid': True,
                'tool': tool_name,
                'args': args,
                'signature': str(signature)
            }
            
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f'Invalid JSON: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }

    def __repr__(self) -> str:
        return f"ToolExecutorAgent(tools={len(self.tool_registry)}, status={self.status})"


# Convenience function for creating ToolExecutorAgent
def create_tool_executor(project_root: str = None, log_file: str = None) -> ToolExecutorAgent:
    """
    Create a new ToolExecutorAgent instance.
    
    Args:
        project_root: Root directory for toolbox operations
        log_file: Path to log file
        
    Returns:
        Configured ToolExecutorAgent instance
    """
    return ToolExecutorAgent(project_root=project_root, log_file=log_file)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    agent = create_tool_executor()
    
    print("🔧 ToolExecutorAgent Example Usage")
    print("=" * 50)
    
    # Display available tools
    tools_info = agent.get_available_tools()
    print(f"Available tools: {tools_info['total_tools']}")
    for tool_name, info in tools_info['available_tools'].items():
        print(f"  - {tool_name}: {info['description']}")
    
    # Example command validation
    test_command = '''
    {
        "tool": "create_file",
        "args": {
            "file_path": "test_agent_file.py",
            "content": "# Created by ToolExecutorAgent\\nprint('Hello from agent!')"
        }
    }
    '''
    
    validation = agent.validate_command(test_command)
    print(f"\\nCommand validation: {'✅' if validation['valid'] else '❌'}")
    if not validation['valid']:
        print(f"Error: {validation['error']}")
    else:
        print(f"Tool: {validation['tool']}")
        print(f"Args: {validation['args']}")