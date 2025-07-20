"""
Simple test to examine CodeEditorAgent output
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.code_editor import CodeEditorAgent
from agents.base import Task


async def test_simple_edit():
    """Test a simple edit and see the output."""
    
    agent = CodeEditorAgent()
    agent.lazy_load_model()
    
    original_code = """def process_data(data):
    result = []
    for item in data:
        processed_item = item * 2
        result.append(processed_item)
    return result"""
    
    instructions = "Rename the variable 'result' to 'output_list' throughout the function"
    
    task = Task(
        prompt=instructions,
        context={
            "code_to_edit": original_code,
            "language": "python"
        }
    )
    
    result = await agent.execute(task)
    
    print("📝 Original Code:")
    print(original_code)
    print("\n🔧 Instructions:")
    print(instructions)
    print(f"\n📊 Status: {result.status}")
    print("\n✅ Edited Code:")
    print(result.output)
    
    # Check if renaming worked
    has_old_var = "result" in result.output
    has_new_var = "output_list" in result.output
    
    print(f"\nAnalysis:")
    print(f"- Contains old variable 'result': {has_old_var}")
    print(f"- Contains new variable 'output_list': {has_new_var}")
    print(f"- Renaming successful: {not has_old_var and has_new_var}")


if __name__ == "__main__":
    asyncio.run(test_simple_edit())