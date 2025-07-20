"""
Quick validation test for the optimized WebResearcherAgent
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.web_researcher_optimized import PerformanceOptimizedWebResearcher
from agents.base import Task


async def test_optimized_agent():
    """Test the optimized agent with a simple request."""
    
    print("🧪 Testing Optimized WebResearcherAgent...")
    
    # Create agent
    agent = PerformanceOptimizedWebResearcher()
    agent.lazy_load_model()
    
    # Test single request
    task = Task(
        prompt="Extract the main heading and first paragraph",
        context={"source_url": "https://httpbin.org/html"}
    )
    
    print("🚀 Testing single request...")
    result = await agent.execute(task)
    
    if result.status == "success":
        print("✅ Single request successful")
        print(f"Performance metrics: {result.output.get('performance_metrics', {})}")
    else:
        print(f"❌ Single request failed: {result.error_message}")
    
    # Test caching
    print("\n🎯 Testing caching...")
    result2 = await agent.execute(task)
    
    if result2.status == "success":
        metrics = result2.output.get('performance_metrics', {})
        if metrics.get('from_cache'):
            print("✅ Caching working correctly")
        else:
            print("⚠️ Cache not used")
    
    await agent.cleanup()
    print("🧹 Agent cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_optimized_agent())