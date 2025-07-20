"""
Performance profiler for WebResearcherAgent to identify bottlenecks
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.web_researcher import WebResearcherAgent
from agents.base import Task


class PerformanceProfiler:
    """Performance profiler for analyzing WebResearcherAgent bottlenecks."""
    
    def __init__(self):
        self.metrics = {}
        
    async def profile_single_request(self, url: str, prompt: str) -> Dict[str, Any]:
        """Profile a single web scraping request."""
        
        print(f"🔍 Profiling: {url}")
        
        # Initialize agent
        agent = WebResearcherAgent()
        start_init = time.time()
        agent.lazy_load_model()
        init_time = time.time() - start_init
        
        # Create task
        task = Task(
            prompt=prompt,
            context={"source_url": url}
        )
        
        # Profile the execution
        start_execution = time.time()
        result = await agent.execute(task)
        execution_time = time.time() - start_execution
        
        return {
            "url": url,
            "init_time": init_time,
            "execution_time": execution_time,
            "total_time": init_time + execution_time,
            "status": result.status,
            "data_size": len(str(result.output)) if result.output else 0
        }
    
    async def profile_concurrent_requests(self, urls: List[str], prompt: str) -> Dict[str, Any]:
        """Profile concurrent requests to identify serialization bottlenecks."""
        
        print(f"🔍 Profiling concurrent requests for {len(urls)} URLs")
        
        # Sequential execution
        start_sequential = time.time()
        sequential_results = []
        for url in urls:
            result = await self.profile_single_request(url, prompt)
            sequential_results.append(result)
        sequential_time = time.time() - start_sequential
        
        # Concurrent execution (with current implementation)
        start_concurrent = time.time()
        tasks = [self.profile_single_request(url, prompt) for url in urls]
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_concurrent
        
        return {
            "sequential_time": sequential_time,
            "concurrent_time": concurrent_time,
            "speedup": sequential_time / concurrent_time if concurrent_time > 0 else 0,
            "sequential_results": sequential_results,
            "concurrent_results": [r for r in concurrent_results if not isinstance(r, Exception)]
        }
    
    async def run_comprehensive_profile(self):
        """Run comprehensive performance profiling."""
        
        print("🚀 Starting comprehensive performance profiling...")
        
        # Test URLs
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json", 
            "https://httpbin.org/xml"
        ]
        
        test_prompt = "Extract the main content and structure from this page"
        
        # Profile single requests
        print("\n📊 Single Request Performance:")
        single_metrics = []
        for url in test_urls:
            metrics = await self.profile_single_request(url, test_prompt)
            single_metrics.append(metrics)
            print(f"  {url}: {metrics['execution_time']:.2f}s")
        
        # Profile concurrent requests
        print("\n📊 Concurrent Request Performance:")
        concurrent_metrics = await self.profile_concurrent_requests(test_urls, test_prompt)
        
        print(f"  Sequential: {concurrent_metrics['sequential_time']:.2f}s")
        print(f"  Concurrent: {concurrent_metrics['concurrent_time']:.2f}s")
        print(f"  Speedup: {concurrent_metrics['speedup']:.2f}x")
        
        # Analyze bottlenecks
        print("\n🔍 Bottleneck Analysis:")
        avg_init_time = sum(m['init_time'] for m in single_metrics) / len(single_metrics)
        avg_execution_time = sum(m['execution_time'] for m in single_metrics) / len(single_metrics)
        
        print(f"  Average initialization time: {avg_init_time:.2f}s")
        print(f"  Average execution time: {avg_execution_time:.2f}s")
        print(f"  Initialization overhead: {(avg_init_time/avg_execution_time)*100:.1f}%")
        
        if concurrent_metrics['speedup'] < 1.5:
            print("  ⚠️  Poor concurrency benefits - likely serialization bottlenecks")
        
        return {
            "single_metrics": single_metrics,
            "concurrent_metrics": concurrent_metrics,
            "bottlenecks": {
                "avg_init_time": avg_init_time,
                "avg_execution_time": avg_execution_time,
                "concurrency_efficiency": concurrent_metrics['speedup']
            }
        }


async def main():
    """Run the performance profiler."""
    profiler = PerformanceProfiler()
    results = await profiler.run_comprehensive_profile()
    
    print("\n📈 Performance Analysis Complete")
    print("=" * 50)
    
    bottlenecks = results['bottlenecks']
    if bottlenecks['avg_init_time'] > 1.0:
        print("🔴 HIGH IMPACT: Model initialization taking too long")
    if bottlenecks['avg_execution_time'] > 5.0:
        print("🔴 HIGH IMPACT: Scraping execution taking too long")
    if bottlenecks['concurrency_efficiency'] < 2.0:
        print("🔴 HIGH IMPACT: Poor concurrent performance")


if __name__ == "__main__":
    asyncio.run(main())