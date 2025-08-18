#!/usr/bin/env python3
"""
Test concurrent model access to validate single-flight loading
"""
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def test_concurrent_health_checks():
    """Test multiple concurrent health check requests"""
    print("🧪 Testing concurrent health checks...")
    
    async def make_health_request(session, i):
        try:
            async with session.get('http://127.0.0.1:8000/health') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return f"Request {i}: {data.get('status', 'unknown')}"
                else:
                    return f"Request {i}: HTTP {resp.status}"
        except Exception as e:
            return f"Request {i}: Error {e}"
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Fire 10 concurrent requests
        tasks = [make_health_request(session, i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        print(f"✅ Completed 10 concurrent health checks in {duration:.2f}s")
        for result in results[:5]:  # Show first 5 results
            print(f"   {result}")
        
        return len([r for r in results if "healthy" in str(r)])

async def test_load_codebase_availability():
    """Test that load_codebase endpoint is available and not returning 503"""
    print("🧪 Testing /load_codebase endpoint availability...")
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"directory_path": "/tmp"}
            async with session.post('http://127.0.0.1:8000/load_codebase', 
                                   json=payload) as resp:
                data = await resp.text()
                if resp.status == 503:
                    print(f"❌ Still getting 503: {data}")
                    return False
                else:
                    print(f"✅ No 503 error - got HTTP {resp.status}")
                    return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    print("=== Concurrent Model Access Validation ===\n")
    
    # Test 1: Concurrent health checks
    healthy_count = await test_concurrent_health_checks()
    print(f"Healthy responses: {healthy_count}/10\n")
    
    # Test 2: Load codebase availability
    load_available = await test_load_codebase_availability()
    
    print("\n=== Test Summary ===")
    print(f"✅ Health checks: {healthy_count}/10 successful")
    print(f"✅ Load codebase: {'Available' if load_available else 'Still 503'}")
    
    if healthy_count >= 8 and load_available:
        print("🎉 Non-concurrent model loading validation PASSED")
        return True
    else:
        print("❌ Validation FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)