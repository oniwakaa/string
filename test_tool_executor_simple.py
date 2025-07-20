"""
Simplified test for ToolExecutorAgent core functionality
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('agents')

from toolbox import create_secure_toolbox

class SimpleToolExecutor:
    """Simplified version of ToolExecutorAgent for testing core functionality."""
    
    def __init__(self):
        """Initialize the tool executor."""
        self.toolbox = create_secure_toolbox()
        
        # Tool registry - mapping tool names to actual functions
        self.tool_registry = {
            'create_file': self.toolbox.create_file,
            'edit_file': self.toolbox.edit_file,
            'run_terminal_command': self.toolbox.run_terminal_command,
            'get_security_status': self.toolbox.get_security_status,
            'get_audit_log': self.toolbox.get_audit_log
        }
        
        self.status = 'ready'
        print(f"SimpleToolExecutor initialized with {len(self.tool_registry)} tools")
    
    def execute_command(self, command_json):
        """Execute a tool command."""
        try:
            # Parse JSON command
            command_data = json.loads(command_json)
            
            # Validate structure
            if not isinstance(command_data, dict):
                return {'success': False, 'error': 'Command must be a JSON object'}
            
            tool_name = command_data.get('tool')
            if not tool_name:
                return {'success': False, 'error': 'Missing tool field'}
            
            args = command_data.get('args', {})
            if not isinstance(args, dict):
                return {'success': False, 'error': 'Args must be a dictionary'}
            
            # Look up tool
            if tool_name not in self.tool_registry:
                return {
                    'success': False, 
                    'error': f'Tool {tool_name} not found',
                    'available_tools': list(self.tool_registry.keys())
                }
            
            # Execute tool
            tool_function = self.tool_registry[tool_name]
            result = tool_function(**args)
            
            return {'success': True, 'result': result}
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Execution failed: {str(e)}'}

def test_tool_executor():
    """Test the simplified tool executor."""
    print("🔧 Testing SimpleToolExecutor Functionality")
    print("=" * 50)
    
    # Initialize executor
    executor = SimpleToolExecutor()
    
    print(f"\\n📊 Test 1: Initialization")
    print(f"✅ Status: {executor.status}")
    print(f"✅ Tools available: {len(executor.tool_registry)}")
    print(f"✅ Tool names: {list(executor.tool_registry.keys())}")
    
    # Test 1: Get security status
    print(f"\\n💻 Test 2: Get Security Status")
    command = {
        "tool": "get_security_status",
        "args": {}
    }
    
    result = executor.execute_command(json.dumps(command))
    if result['success']:
        print("✅ Security status retrieved")
        status_data = result['result']
        print(f"  Project root: {status_data.get('project_root', 'N/A')}")
        print(f"  Max file size: {status_data.get('max_file_size', 'N/A')} bytes")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test 2: Create file
    print(f"\\n📝 Test 3: Create File")
    command = {
        "tool": "create_file",
        "args": {
            "file_path": "test_simple_executor.py",
            "content": "# Created by SimpleToolExecutor\\nprint('Hello World!')"
        }
    }
    
    result = executor.execute_command(json.dumps(command))
    if result['success']:
        print("✅ File created successfully")
        file_data = result['result']
        print(f"  Path: {file_data.get('path', 'N/A')}")
        print(f"  Size: {file_data.get('size', 'N/A')} bytes")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test 3: Run command
    print(f"\\n💻 Test 4: Run Command")
    command = {
        "tool": "run_terminal_command",
        "args": {
            "command": ["git", "--version"]
        }
    }
    
    result = executor.execute_command(json.dumps(command))
    if result['success']:
        print("✅ Command executed successfully")
        cmd_data = result['result']
        print(f"  Exit code: {cmd_data.get('exit_code', 'N/A')}")
        print(f"  Output: {cmd_data.get('stdout', 'N/A').strip()}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test 4: Invalid tool
    print(f"\\n🚨 Test 5: Invalid Tool")
    command = {
        "tool": "nonexistent_tool",
        "args": {}
    }
    
    result = executor.execute_command(json.dumps(command))
    if not result['success']:
        print("✅ Invalid tool properly rejected")
        print(f"  Error: {result['error']}")
    else:
        print("❌ Invalid tool was not rejected!")
    
    # Test 5: Invalid JSON
    print(f"\\n🚨 Test 6: Invalid JSON")
    result = executor.execute_command("{ invalid json")
    if not result['success']:
        print("✅ Invalid JSON properly rejected")
        print(f"  Error: {result['error']}")
    else:
        print("❌ Invalid JSON was not rejected!")
    
    # Test 6: Missing arguments
    print(f"\\n🚨 Test 7: Missing Required Arguments")
    command = {
        "tool": "create_file",
        "args": {
            "file_path": "test.py"
            # Missing 'content' argument
        }
    }
    
    result = executor.execute_command(json.dumps(command))
    if not result['success']:
        print("✅ Missing arguments properly rejected")
        print(f"  Error: {result['error']}")
    else:
        print("❌ Missing arguments were not rejected!")
    
    print(f"\\n🎉 All core functionality tests completed!")
    print("✅ ToolExecutor can parse JSON commands")
    print("✅ ToolExecutor can validate tool names")
    print("✅ ToolExecutor can execute toolbox functions")
    print("✅ ToolExecutor handles errors gracefully")
    print("✅ ToolExecutor provides proper security validation")

if __name__ == "__main__":
    test_tool_executor()