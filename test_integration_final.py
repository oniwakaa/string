"""
Final integration test for CodeEditorAgent with ProjectManager
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import ProjectManager


async def test_code_editing_workflow():
    """Test the complete code editing workflow through ProjectManager."""
    
    print("🔗 Testing CodeEditorAgent Integration with ProjectManager")
    print("=" * 60)
    
    # Create ProjectManager
    pm = ProjectManager()
    
    # Test 1: Bug fix workflow
    print("\n📝 Test 1: Bug Fix Workflow")
    test_prompt = "Fix the bug in the calculate_total function by adding null checks"
    
    plan = await pm._decompose_prompt(test_prompt)
    print(f"Generated plan steps: {len(plan)}")
    
    for i, step in enumerate(plan, 1):
        print(f"  Step {i}: {step['agent_role']} - {step['prompt'][:80]}...")
    
    has_code_editor = any(step['agent_role'] == 'code_editor' for step in plan)
    print(f"Code editor in workflow: {'✅ Yes' if has_code_editor else '❌ No'}")
    
    # Test 2: Direct editing workflow
    print("\n📝 Test 2: Direct Code Editing")
    
    # Simulate a direct editing request with provided code
    direct_edit_request = "edit this code to add type hints"
    
    # Test with provided context
    sample_code = """def add_numbers(a, b):
    return a + b"""
    
    # Create a task directly
    from agents.base import Task
    
    task = Task(
        prompt=direct_edit_request,
        context={
            "code_to_edit": sample_code,
            "language": "python"
        }
    )
    
    # Test the code editor agent directly
    code_editor = pm.agents['code_editor']
    result = await code_editor.execute(task)
    
    print(f"Direct editing status: {result.status}")
    if result.status == "success":
        print("✅ CodeEditorAgent working correctly")
        print(f"Original: {sample_code}")
        print(f"Edited: {result.output}")
    else:
        print(f"❌ Error: {result.error_message}")
    
    # Test 3: Agent status
    print("\n📊 Agent Status Check")
    agent_statuses = pm.get_agent_status()
    
    for agent_name, status in agent_statuses.items():
        status_icon = "✅" if status == "ready" else "⚠️"
        print(f"  {status_icon} {agent_name}: {status}")
    
    code_editor_ready = agent_statuses.get('code_editor') == 'ready'
    print(f"\nCodeEditorAgent ready: {'✅ Yes' if code_editor_ready else '❌ No'}")
    
    # Cleanup
    await pm.cleanup()
    
    # Summary
    print(f"\n🎯 INTEGRATION TEST SUMMARY")
    print("=" * 40)
    print(f"✅ CodeEditorAgent registered: Yes")
    print(f"{'✅' if has_code_editor else '❌'} Bug fix workflow detection: {'Yes' if has_code_editor else 'No'}")
    print(f"{'✅' if result.status == 'success' else '❌'} Direct editing functionality: {'Yes' if result.status == 'success' else 'No'}")
    print(f"{'✅' if code_editor_ready else '❌'} Agent initialization: {'Yes' if code_editor_ready else 'No'}")
    
    overall_success = has_code_editor and result.status == "success" and code_editor_ready
    print(f"\n{'🎉' if overall_success else '⚠️'} Overall Integration: {'SUCCESS' if overall_success else 'NEEDS REVIEW'}")


if __name__ == "__main__":
    asyncio.run(test_code_editing_workflow())