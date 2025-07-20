"""
Performance benchmark comparing original vs optimized WebResearcherAgent
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.web_researcher import WebResearcherAgent
from agents.web_researcher_optimized import PerformanceOptimizedWebResearcher
from agents.base import Task


class PerformanceBenchmark:
    """Comprehensive performance benchmark suite."""
    
    def __init__(self):
        self.test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/xml",
            "https://example.com",
            "https://httpbin.org/robots.txt"
        ]
        
        self.test_prompts = [
            "Extract the main heading and first paragraph",
            "Get the title and meta description",
            "List all links and their text",
            "Extract the main content structure",
            "Analyze the page content and provide a summary"
        ]
    
    async def benchmark_agent(self, agent_class, name: str, tasks: List[Task]) -> Dict[str, Any]:
        """Benchmark a specific agent implementation."""
        print(f"\n🧪 Benchmarking {name}...")
        
        # Initialize agent
        agent = agent_class()
        init_start = time.time()
        agent.lazy_load_model()
        init_time = time.time() - init_start
        
        # Single request performance
        single_times = []
        print(f"  📊 Single request performance:")
        
        for i, task in enumerate(tasks[:3]):  # Test first 3 tasks
            start_time = time.time()
            result = await agent.execute(task)
            execution_time = time.time() - start_time
            single_times.append(execution_time)
            
            status_icon = "✅" if result.status == "success" else "❌"
            print(f"    {status_icon} Task {i+1}: {execution_time:.2f}s")
        
        avg_single_time = sum(single_times) / len(single_times)
        
        # Concurrent request performance
        print(f"  🚀 Concurrent performance ({len(tasks)} tasks):")
        concurrent_start = time.time()
        
        if hasattr(agent, 'execute_batch'):
            # Use optimized batch execution
            concurrent_results = await agent.execute_batch(tasks)
        else:
            # Standard concurrent execution
            concurrent_results = await asyncio.gather(
                *[agent.execute(task) for task in tasks],
                return_exceptions=True
            )
        
        concurrent_time = time.time() - concurrent_start
        
        # Calculate success rate
        successful_results = [r for r in concurrent_results if not isinstance(r, Exception) and getattr(r, 'status', None) == 'success']
        success_rate = len(successful_results) / len(tasks) * 100
        
        # Cleanup
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()
        
        return {
            'name': name,
            'init_time': init_time,
            'avg_single_time': avg_single_time,
            'concurrent_time': concurrent_time,
            'success_rate': success_rate,
            'throughput': len(tasks) / concurrent_time if concurrent_time > 0 else 0,
            'results': concurrent_results
        }
    
    async def run_comprehensive_benchmark(self):
        """Run comprehensive performance comparison."""
        print("🚀 Starting Comprehensive Performance Benchmark")
        print("=" * 60)
        
        # Create test tasks
        tasks = []
        for i, (url, prompt) in enumerate(zip(self.test_urls, self.test_prompts)):
            task = Task(
                prompt=prompt,
                context={"source_url": url}
            )
            tasks.append(task)
        
        print(f"📋 Testing with {len(tasks)} different URL/prompt combinations")
        
        # Benchmark original agent
        original_results = await self.benchmark_agent(
            WebResearcherAgent, 
            "Original WebResearcherAgent", 
            tasks
        )
        
        # Benchmark optimized agent
        optimized_results = await self.benchmark_agent(
            PerformanceOptimizedWebResearcher, 
            "Optimized WebResearcherAgent", 
            tasks
        )
        
        # Performance comparison
        print("\n📈 PERFORMANCE COMPARISON")
        print("=" * 60)
        
        # Speed improvements
        single_speedup = original_results['avg_single_time'] / optimized_results['avg_single_time']
        concurrent_speedup = original_results['concurrent_time'] / optimized_results['concurrent_time']
        throughput_improvement = (optimized_results['throughput'] / original_results['throughput'] - 1) * 100
        
        print(f"⚡ Single Request Speed:")
        print(f"   Original: {original_results['avg_single_time']:.2f}s")
        print(f"   Optimized: {optimized_results['avg_single_time']:.2f}s")
        print(f"   Speedup: {single_speedup:.2f}x ({(single_speedup-1)*100:.1f}% faster)")
        
        print(f"\n🚀 Concurrent Processing:")
        print(f"   Original: {original_results['concurrent_time']:.2f}s")
        print(f"   Optimized: {optimized_results['concurrent_time']:.2f}s")
        print(f"   Speedup: {concurrent_speedup:.2f}x ({(concurrent_speedup-1)*100:.1f}% faster)")
        
        print(f"\n📊 Throughput:")
        print(f"   Original: {original_results['throughput']:.2f} req/s")
        print(f"   Optimized: {optimized_results['throughput']:.2f} req/s")
        print(f"   Improvement: {throughput_improvement:.1f}%")
        
        print(f"\n✅ Success Rate:")
        print(f"   Original: {original_results['success_rate']:.1f}%")
        print(f"   Optimized: {optimized_results['success_rate']:.1f}%")
        
        # Performance summary
        print(f"\n🎯 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        if single_speedup >= 2.0:
            print("🟢 EXCELLENT: Single request performance improved by 2x or more")
        elif single_speedup >= 1.5:
            print("🟡 GOOD: Single request performance improved by 1.5x or more")
        else:
            print("🔴 NEEDS WORK: Single request performance improvement < 1.5x")
        
        if concurrent_speedup >= 3.0:
            print("🟢 EXCELLENT: Concurrent performance improved by 3x or more")
        elif concurrent_speedup >= 2.0:
            print("🟡 GOOD: Concurrent performance improved by 2x or more")
        else:
            print("🔴 NEEDS WORK: Concurrent performance improvement < 2x")
        
        if optimized_results['success_rate'] >= 90:
            print("🟢 EXCELLENT: High success rate maintained")
        elif optimized_results['success_rate'] >= 80:
            print("🟡 GOOD: Acceptable success rate")
        else:
            print("🔴 ISSUE: Low success rate - reliability concerns")
        
        # Detailed metrics for analysis
        return {
            'original': original_results,
            'optimized': optimized_results,
            'improvements': {
                'single_speedup': single_speedup,
                'concurrent_speedup': concurrent_speedup,
                'throughput_improvement': throughput_improvement
            }
        }

    async def test_caching_performance(self):
        """Test caching performance specifically."""
        print("\n🎯 CACHING PERFORMANCE TEST")
        print("=" * 40)
        
        # Create agent
        agent = PerformanceOptimizedWebResearcher()
        agent.lazy_load_model()
        
        # Test same URL multiple times
        test_url = "https://httpbin.org/html"
        test_prompt = "Extract the main content"
        
        # First request (no cache)
        task = Task(prompt=test_prompt, context={"source_url": test_url})
        
        start_time = time.time()
        result1 = await agent.execute(task)
        first_time = time.time() - start_time
        
        # Second request (should hit cache)
        start_time = time.time()
        result2 = await agent.execute(task)
        second_time = time.time() - start_time
        
        cache_speedup = first_time / second_time if second_time > 0 else 0
        
        print(f"   First request (no cache): {first_time:.2f}s")
        print(f"   Second request (cached): {second_time:.2f}s")
        print(f"   Cache speedup: {cache_speedup:.2f}x")
        
        await agent.cleanup()
        
        return cache_speedup


async def main():
    """Run the performance benchmark."""
    benchmark = PerformanceBenchmark()
    
    # Run comprehensive benchmark
    results = await benchmark.run_comprehensive_benchmark()
    
    # Test caching
    cache_speedup = await benchmark.test_caching_performance()
    
    # Final recommendations
    print(f"\n💡 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 60)
    
    improvements = results['improvements']
    
    if improvements['concurrent_speedup'] >= 2.0:
        print("✅ Concurrent processing optimization: SUCCESS")
    else:
        print("⚠️  Concurrent processing could be further optimized")
    
    if cache_speedup >= 5.0:
        print("✅ Caching optimization: SUCCESS")
    else:
        print("⚠️  Caching could be further optimized")
    
    if improvements['single_speedup'] >= 1.5:
        print("✅ Single request optimization: SUCCESS")
    else:
        print("⚠️  Single request processing could be further optimized")


if __name__ == "__main__":
    asyncio.run(main())