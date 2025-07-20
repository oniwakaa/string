"""
Simplified integration test for orchestrator with ToolExecutorAgent (no pydantic dependency)
"""

import sys
import os
import asyncio
import json
from uuid import uuid4

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('agents')

from toolbox import create_secure_toolbox

# Simple Task and Result classes for testing
class SimpleTask:
    def __init__(self, prompt, context=None):
        self.task_id = uuid4()
        self.prompt = prompt
        self.context = context or {}

class SimpleResult:
    def __init__(self, task_id, status, output, error_message=None, metadata=None):
        self.task_id = task_id
        self.status = status
        self.output = output
        self.error_message = error_message
        self.metadata = metadata or {}

# Simple ToolExecutor for testing
class SimpleToolExecutor:
    def __init__(self):
        self.toolbox = create_secure_toolbox()
        self.tool_registry = {
            'create_file': self.toolbox.create_file,
            'edit_file': self.toolbox.edit_file,
            'run_terminal_command': self.toolbox.run_terminal_command,
            'get_security_status': self.toolbox.get_security_status,
            'get_audit_log': self.toolbox.get_audit_log
        }
        self.status = 'ready'
    
    async def execute(self, task):
        """Execute a tool command (async wrapper for sync operations)."""
        try:
            # Parse JSON command
            command_data = json.loads(task.prompt)
            tool_name = command_data.get('tool')
            args = command_data.get('args', {})
            
            if tool_name not in self.tool_registry:
                return SimpleResult(
                    task.task_id, "failure", "", 
                    f"Tool {tool_name} not found"
                )
            
            # Execute tool
            tool_function = self.tool_registry[tool_name]
            result = tool_function(**args)
            
            return SimpleResult(task.task_id, "success", result)
            
        except Exception as e:
            return SimpleResult(
                task.task_id, "failure", "", str(e)
            )

# Mock cognitive agents
class MockCodeGenerator:
    def __init__(self):
        self.status = "ready"
    
    async def execute(self, task):
        """Mock code generation with next_action."""
        generated_code = f"""# Generated code for: {task.prompt}
def example_function():
    print("Hello from generated code!")
    return True

if __name__ == "__main__":
    result = example_function()
    print(f"Success: {{result}}")
"""
        
        metadata = {
            'next_action': {
                'tool': 'create_file',
                'args': {
                    'file_path': 'example_generated.py',
                    'content': generated_code
                }
            }
        }
        
        return SimpleResult(
            task.task_id, "success", generated_code, metadata=metadata
        )

class MockCodeEditor:
    def __init__(self):
        self.status = "ready"
    
    async def execute(self, task):
        """Mock code editing with next_action."""
        original_code = task.context.get('code_to_edit', '')
        edited_code = f"# Edited by MockCodeEditor\n{original_code}"
        
        metadata = {
            'next_action': {
                'tool': 'edit_file',
                'args': {
                    'file_path': 'example_edited.py',
                    'content': edited_code,
                    'create_backup': True
                }
            }
        }
        
        return SimpleResult(
            task.task_id, "success", edited_code, metadata=metadata
        )

# Simple Orchestrator
class SimpleOrchestrator:
    def __init__(self):
        self.agents = {
            'code_generator': MockCodeGenerator(),
            'code_editor': MockCodeEditor(),
            'tool_executor': SimpleToolExecutor()
        }
    
    def _handle_next_action(self, result):
        """Handle next_action metadata and create tool execution tasks."""
        if not result.metadata or 'next_action' not in result.metadata:
            return None
        
        next_action = result.metadata['next_action']
        tool_command = {
            "tool": next_action.get('tool'),
            "args": next_action.get('args', {})
        }
        
        return SimpleTask(
            prompt=json.dumps(tool_command),
            context={"triggered_by": "next_action"}
        )
    
    async def execute_workflow(self, agent_role, task):
        """Execute a complete workflow with tool actions."""
        # Execute main task
        agent = self.agents[agent_role]
        result = await agent.execute(task)
        
        if result.status != "success":
            return result, None
        
        # Handle next_action
        tool_task = self._handle_next_action(result)
        if tool_task:
            tool_agent = self.agents['tool_executor']
            tool_result = await tool_agent.execute(tool_task)
            return result, tool_result
        
        return result, None

async def test_integration():
    """Test the orchestrator integration."""
    print("🔗 Testing Orchestrator Integration")
    print("=" * 50)
    
    orchestrator = SimpleOrchestrator()
    
    # Test 1: Code Generation → File Creation
    print("\n📝 Test 1: Code Generation → File Creation")
    task1 = SimpleTask("Generate a hello world function")
    
    main_result, tool_result = await orchestrator.execute_workflow('code_generator', task1)
    
    test1_success = (
        main_result.status == "success" and 
        tool_result and tool_result.status == "success"
    )
    
    if test1_success:
        print("✅ Code generation and file creation successful")
        file_data = tool_result.output
        print(f"  Created file: {file_data.get('path', 'N/A')}")
    else:
        print("❌ Code generation flow failed")
        if main_result.status != "success":
            print(f"  Main error: {main_result.error_message}")
        if tool_result and tool_result.status != "success":
            print(f"  Tool error: {tool_result.error_message}")
    
    # Test 2: Code Editing → File Update
    print("\n📝 Test 2: Code Editing → File Update")
    task2 = SimpleTask(
        "Add comments to this function",
        context={'code_to_edit': 'def test():\n    return True'}
    )
    
    main_result2, tool_result2 = await orchestrator.execute_workflow('code_editor', task2)
    
    test2_success = (
        main_result2.status == "success" and 
        tool_result2 and tool_result2.status == "success"
    )
    
    if test2_success:
        print("✅ Code editing and file update successful")
        file_data = tool_result2.output
        print(f"  Updated file: {file_data.get('path', 'N/A')}")
    else:
        print("❌ Code editing flow failed")
    
    # Test 3: Direct Tool Usage
    print("\n💻 Test 3: Direct Tool Usage")
    tool_task = SimpleTask(json.dumps({
        "tool": "get_security_status",
        "args": {}
    }))
    
    tool_agent = orchestrator.agents['tool_executor']
    direct_result = await tool_agent.execute(tool_task)
    
    if direct_result.status == "success":
        print("✅ Direct tool execution successful")
        status_data = direct_result.output
        print(f"  Project root: {status_data.get('project_root', 'N/A')}")
    else:
        print(f"❌ Direct tool execution failed: {direct_result.error_message}")
    
    # Test 4: Command Execution
    print("\n🔧 Test 4: Command Execution")
    cmd_task = SimpleTask(json.dumps({
        "tool": "run_terminal_command",
        "args": {"command": ["git", "--version"]}
    }))
    
    cmd_result = await tool_agent.execute(cmd_task)
    
    if cmd_result.status == "success":
        print("✅ Command execution successful")
        cmd_data = cmd_result.output
        print(f"  Output: {cmd_data.get('stdout', 'N/A').strip()}")
    else:
        print(f"❌ Command execution failed: {cmd_result.error_message}")
    
    # Summary
    print("\n📊 Integration Test Results")
    print("=" * 40)
    
    tests = [
        ("Code Gen → File Creation", test1_success),
        ("Code Edit → File Update", test2_success),
        ("Direct Tool Execution", direct_result.status == "success"),
        ("Command Execution", cmd_result.status == "success")
    ]
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    for test_name, success in tests:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All integration tests successful!")
        print("🚀 Orchestrator ready for ToolExecutorAgent integration!")
    else:
        print("⚠️ Some tests failed - review implementation")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Integration test complete")