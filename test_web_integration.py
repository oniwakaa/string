"""
Test script for WebResearcherAgent integration with ProjectManager
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import ProjectManager


async def test_web_researcher_integration():
    """Test the integration of WebResearcherAgent with ProjectManager."""
    
    print("🧪 Testing WebResearcherAgent integration with ProjectManager...")
    
    # Create ProjectManager instance
    pm = ProjectManager()
    
    # Check if web_researcher agent is registered
    print(f"📋 Available agents: {list(pm.agents.keys())}")
    
    if 'web_researcher' not in pm.agents:
        print("❌ WebResearcherAgent not found in agent registry!")
        return
    
    print("✅ WebResearcherAgent found in agent registry")
    
    # Test web research task detection and execution
    test_prompt = "Extract the main heading and description from https://httpbin.org/html"
    
    print(f"\n🚀 Testing web research with prompt: '{test_prompt}'")
    
    # Execute the request through ProjectManager
    result = await pm.handle_request(test_prompt)
    
    print(f"\n📊 Request completed with status: {result['status']}")
    
    if result['status'] == 'success':
        print("✅ Web research integration successful!")
        print(f"📄 Result: {result['result']}")
        print(f"📋 Execution plan: {result['execution_plan']}")
        print(f"🔢 Tasks executed: {result['tasks_executed']}")
    else:
        print(f"❌ Integration test failed: {result['message']}")
    
    # Test agent status
    print(f"\n📊 Agent statuses: {pm.get_agent_status()}")
    
    # Cleanup
    await pm.cleanup()


async def test_complex_web_workflow():
    """Test a complex workflow involving web research and code generation."""
    
    print("\n🧪 Testing complex web research + code generation workflow...")
    
    pm = ProjectManager()
    
    # Test prompt that should trigger web research followed by code generation
    complex_prompt = "Scrape the main content from https://httpbin.org/html and generate Python code to parse similar HTML"
    
    print(f"🚀 Testing complex workflow with prompt: '{complex_prompt}'")
    
    result = await pm.handle_request(complex_prompt)
    
    print(f"\n📊 Complex workflow completed with status: {result['status']}")
    
    if result['status'] == 'success':
        print("✅ Complex web research workflow successful!")
        print(f"📄 Final result preview: {str(result['result'])[:200]}...")
        print(f"📋 Execution plan steps: {len(result['execution_plan'])}")
    else:
        print(f"❌ Complex workflow failed: {result['message']}")
    
    await pm.cleanup()


if __name__ == "__main__":
    # Run both test scenarios
    asyncio.run(test_web_researcher_integration())
    asyncio.run(test_complex_web_workflow())