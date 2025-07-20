"""
Test script for WebResearcherAgent
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.web_researcher import WebResearcherAgent
from agents.base import Task


async def test_web_researcher():
    """Test the WebResearcherAgent with a simple web scraping task."""
    
    print("🧪 Testing WebResearcherAgent...")
    
    # Create agent instance
    agent = WebResearcherAgent()
    
    # Test model loading
    try:
        agent.lazy_load_model()
        print(f"✅ Agent initialized successfully: {agent}")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return
    
    # Create a test task
    task = Task(
        prompt="Extract the main heading and first paragraph from this webpage",
        context={
            "source_url": "https://httpbin.org/html"  # Simple test page
        }
    )
    
    print(f"📋 Task created: {task.task_id}")
    print(f"🌐 Target URL: {task.context['source_url']}")
    print(f"📝 Extraction prompt: {task.prompt}")
    
    # Execute the task
    print("\n🚀 Executing web research task...")
    result = await agent.execute(task)
    
    # Display results
    print(f"\n📊 Task completed with status: {result.status}")
    
    if result.status == "success":
        print("✅ Successfully extracted data:")
        print(f"📄 Data: {result.output}")
    else:
        print(f"❌ Task failed: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(test_web_researcher())