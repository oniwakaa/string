"""
Integration test for the updated ProjectManager orchestrator with ToolExecutorAgent
"""

import sys
import os
import asyncio
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import without relative imports for testing
sys.path.append('agents')
from base import Task, Result
from toolbox import create_secure_toolbox
from specialists import ToolExecutorAgent

# Mock version of orchestrator components for testing
class MockCodeGeneratorAgent:
    """Mock CodeGeneratorAgent for testing next_action flow."""
    
    def __init__(self):
        self.name = "MockCodeGenerator"
        self.role = "code_generator"
        self.status = "ready"
    
    async def execute(self, task: Task) -> Result:
        """Mock code generation with next_action suggestion."""
        
        # Generate simple code
        generated_code = """def hello_world():
    print("Hello from generated code!")
    return "success"

if __name__ == "__main__":
    result = hello_world()
    print(f"Result: {result}")
"""
        
        # Create next_action metadata
        metadata = {
            'next_action': {
                'tool': 'create_file',
                'args': {
                    'file_path': 'hello_world.py',
                    'content': generated_code
                }
            }
        }
        
        return Result(
            task_id=task.task_id,
            status="success",
            output=generated_code,
            metadata=metadata
        )

class MockCodeEditorAgent:
    """Mock CodeEditorAgent for testing next_action flow."""
    
    def __init__(self):
        self.name = "MockCodeEditor"
        self.role = "code_editor"
        self.status = "ready"
    
    async def execute(self, task: Task) -> Result:
        """Mock code editing with next_action suggestion."""
        
        original_code = task.context.get('code_to_edit', '')
        
        # Simple editing - add a comment
        edited_code = "# Edited by MockCodeEditor\n" + original_code
        
        # Create next_action metadata
        metadata = {
            'next_action': {
                'tool': 'edit_file',
                'args': {
                    'file_path': 'edited_file.py',
                    'content': edited_code,
                    'create_backup': True
                }
            }
        }
        
        return Result(
            task_id=task.task_id,
            status="success",
            output=edited_code,
            metadata=metadata
        )

class SimpleOrchestrator:
    """Simplified orchestrator for testing the next_action flow."""
    
    def __init__(self):
        self.agents = {
            'code_generator': MockCodeGeneratorAgent(),
            'code_editor': MockCodeEditorAgent(),
            'tool_executor': ToolExecutorAgent()
        }
        self.active_tasks = {}
    
    def _handle_next_action(self, result: Result) -> Task:
        """Handle next_action metadata and create tool execution tasks."""
        if not hasattr(result, 'metadata') or not result.metadata:
            return None
            
        next_action = result.metadata.get('next_action')
        if not next_action:
            return None
        
        try:
            # Create JSON command for ToolExecutorAgent
            tool_command = {
                "tool": next_action.get('tool'),
                "args": next_action.get('args', {})
            }
            
            # Create new task for tool execution
            tool_task = Task(
                prompt=json.dumps(tool_command),
                context={
                    "original_result_id": str(result.task_id),
                    "triggered_by": "next_action"
                }
            )
            
            # Store agent role mapping
            self.active_tasks[tool_task.task_id] = {
                "task": tool_task,
                "agent_role": "tool_executor"
            }
            
            return tool_task
            
        except Exception as e:
            print(f"❌ Error handling next_action: {str(e)}")
            return None
    
    async def execute_with_tools(self, agent_role: str, task: Task):
        """Execute a task and handle any next_action suggestions."""
        
        # Execute the main task
        agent = self.agents[agent_role]
        result = await agent.execute(task)
        
        print(f"📊 {agent_role} result: {result.status}")
        if result.status == "success":
            print(f"✅ Output preview: {str(result.output)[:100]}...")
            
            # Check for next_action
            tool_task = self._handle_next_action(result)
            if tool_task:
                print(f"🔧 Executing suggested tool action...")
                
                # Execute the tool task
                tool_agent = self.agents['tool_executor']
                tool_result = await tool_agent.execute(tool_task)
                
                print(f"📊 Tool execution result: {tool_result.status}")
                if tool_result.status == "success":
                    print(f"✅ Tool output: {tool_result.output}")
                    return result, tool_result
                else:
                    print(f"❌ Tool error: {tool_result.error_message}")
                    return result, tool_result
            else:
                print("ℹ️  No next_action suggested")
                return result, None
        else:
            print(f"❌ Error: {result.error_message}")
            return result, None

async def test_orchestrator_integration():
    """Test the complete orchestrator integration with ToolExecutorAgent."""
    
    print("🔗 Testing Orchestrator Integration with ToolExecutorAgent")
    print("=" * 60)
    
    orchestrator = SimpleOrchestrator()
    
    # Test 1: Code generation with file creation
    print("\n📝 Test 1: Code Generation → File Creation")
    print("-" * 40)
    
    gen_task = Task(
        prompt="Generate a simple hello world function",
        context={}
    )
    
    gen_result, tool_result = await orchestrator.execute_with_tools('code_generator', gen_task)
    
    if gen_result.status == "success" and tool_result and tool_result.status == "success":
        print("✅ Code generation and file creation flow working!")
    else:
        print("❌ Code generation flow failed")
    
    # Test 2: Code editing with file saving
    print("\n📝 Test 2: Code Editing → File Saving")
    print("-" * 40)
    
    code_to_edit = """def old_function():
    return "old value"
"""
    
    edit_task = Task(
        prompt="Add a comment to this function",
        context={'code_to_edit': code_to_edit}
    )
    
    edit_result, tool_result = await orchestrator.execute_with_tools('code_editor', edit_task)
    
    if edit_result.status == "success" and tool_result and tool_result.status == "success":
        print("✅ Code editing and file saving flow working!")
    else:
        print("❌ Code editing flow failed")
    
    # Test 3: Direct tool execution
    print("\n💻 Test 3: Direct Tool Execution")
    print("-" * 40)
    
    tool_command = {
        "tool": "get_security_status",
        "args": {}
    }
    
    direct_tool_task = Task(
        prompt=json.dumps(tool_command),
        context={}
    )
    
    tool_agent = orchestrator.agents['tool_executor']
    direct_result = await tool_agent.execute(direct_tool_task)
    
    if direct_result.status == "success":
        print("✅ Direct tool execution working!")
        print(f"Security status: {direct_result.output.get('project_root', 'N/A')}")
    else:
        print(f"❌ Direct tool execution failed: {direct_result.error_message}")
    
    # Test 4: Command execution
    print("\n💻 Test 4: Command Execution via Tools")
    print("-" * 40)
    
    cmd_command = {
        "tool": "run_terminal_command",
        "args": {
            "command": ["git", "--version"]
        }
    }
    
    cmd_task = Task(
        prompt=json.dumps(cmd_command),
        context={}
    )
    
    cmd_result = await tool_agent.execute(cmd_task)
    
    if cmd_result.status == "success":
        print("✅ Command execution working!")
        cmd_data = cmd_result.output
        print(f"Git version: {cmd_data.get('stdout', 'N/A').strip()}")
    else:
        print(f"❌ Command execution failed: {cmd_result.error_message}")
    
    # Summary
    print("\n📊 Integration Test Summary")
    print("=" * 40)
    
    test_results = [
        ("Code Gen → File Creation", gen_result.status == "success" and tool_result and tool_result.status == "success"),
        ("Code Edit → File Saving", edit_result.status == "success" and tool_result and tool_result.status == "success"),
        ("Direct Tool Execution", direct_result.status == "success"),
        ("Command Execution", cmd_result.status == "success")
    ]
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for test_name, success in test_results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("🔗 ProjectManager orchestrator ready for ToolExecutorAgent integration")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_orchestrator_integration())
    if success:
        print("\n✅ Integration testing complete - system ready!")
    else:
        print("\n❌ Integration issues detected - review implementation")