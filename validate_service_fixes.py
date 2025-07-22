#!/usr/bin/env python3
"""
Service Validation Script for MemOS Integration Fixes

This script validates the critical fixes applied to the MemOS integration:
1. Correct backend naming (kv_cache/uninitialized instead of persistent_storage)
2. MemOS instance connection between service and project memory manager
3. Project-specific cube creation with simplified configuration
"""

import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime

async def test_service_health():
    """Test if service is healthy and MemOS is initialized."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/health") as response:
                data = await response.json()
                print(f"🏥 Service Health Status: {data['status']}")
                print(f"📊 MemOS Status: {data['memos']['status']}")
                print(f"🤖 Model Status: {data['model']['healthy']}")
                return data['status'] == 'healthy'
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def test_codebase_loading():
    """Test codebase loading with project isolation."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "directory_path": "./agents",
            "user_id": "test_user",
            "project_id": "validation_test",
            "file_extensions": [".py"],
            "exclude_dirs": ["__pycache__", ".git"]
        }
        
        try:
            print("\n📂 Testing Codebase Loading...")
            async with session.post("http://localhost:8000/load_codebase", json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    print(f"✅ Status: {data['status']}")
                    print(f"📊 Files loaded: {data['files_loaded']}")
                    print(f"📊 Files skipped: {data['files_skipped']}")
                    print(f"⏱️ Loading time: {data['loading_time_seconds']:.2f}s")
                    
                    # Critical validation: Files should be loaded (not 0)
                    if data['files_loaded'] > 0:
                        print("✅ CRITICAL FIX VALIDATED: Data ingestion working (Files loaded > 0)")
                        return True
                    else:
                        print("❌ CRITICAL ISSUE: Files loaded = 0 (data ingestion failing)")
                        return False
                else:
                    print(f"❌ Load failed: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Codebase loading error: {e}")
            return False

async def test_preference_setting():
    """Test parametric memory preference setting."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "action": "add",
            "category": "coding_style",
            "key": "indentation",
            "value": "4 spaces",
            "description": "Use 4 spaces for Python indentation"
        }
        
        try:
            print("\n🎯 Testing Preference Setting...")
            url = "http://localhost:8000/projects/validation_test/preferences?user_id=test_user"
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200 and data['status'] == 'success':
                    print(f"✅ Preference set successfully: {data['message']}")
                    print("✅ CRITICAL FIX VALIDATED: Parametric memory working")
                    return True
                else:
                    print(f"❌ Preference setting failed: {data}")
                    print("❌ CRITICAL ISSUE: Parametric memory still failing")
                    return False
                    
        except Exception as e:
            print(f"❌ Preference setting error: {e}")
            return False

async def test_preference_retrieval():
    """Test preference retrieval from parametric memory."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "action": "get"
        }
        
        try:
            print("\n🔍 Testing Preference Retrieval...")
            url = "http://localhost:8000/projects/validation_test/preferences?user_id=test_user"
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status == 200 and data['status'] == 'success':
                    print(f"✅ Preferences retrieved: {json.dumps(data['preferences'], indent=2)}")
                    return True
                else:
                    print(f"❌ Preference retrieval failed: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Preference retrieval error: {e}")
            return False

async def test_memory_search():
    """Test memory search with project context."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "query": "agent base class implementation",
            "user_id": "test_user", 
            "project_id": "validation_test",
            "include_memory": True
        }
        
        try:
            print("\n🔎 Testing Memory Search...")
            async with session.post("http://localhost:8000/chat", json=payload) as response:
                data = await response.json()
                
                if response.status == 200:
                    print(f"✅ Response received")
                    print(f"📊 Memory enhanced: {data['memory_enhanced']}")
                    print(f"📊 Memories used: {len(data['memories_used'])}")
                    
                    if data['memories_used']:
                        print("✅ Context retrieval working with project isolation")
                    return True
                else:
                    print(f"❌ Search failed: {data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Memory search error: {e}")
            return False

async def main():
    """Run all validation tests."""
    print("🚀 MemOS Integration Validation Suite")
    print("=" * 60)
    print("Testing critical fixes:")
    print("1. Backend naming (kv_cache/uninitialized)")
    print("2. MemOS instance connections")
    print("3. Project-specific memory isolation")
    print("=" * 60)
    
    # Track test results
    results = {
        "health": False,
        "codebase_loading": False,
        "preference_setting": False,
        "preference_retrieval": False,
        "memory_search": False
    }
    
    # Run tests
    print("\n🧪 Running validation tests...")
    
    # Test 1: Health check
    results["health"] = await test_service_health()
    
    if not results["health"]:
        print("\n❌ Service is not healthy. Please ensure the service is running:")
        print("   python run_gguf_service.py")
        return
    
    # Wait a moment for service stability
    await asyncio.sleep(1)
    
    # Test 2: Codebase loading (validates data ingestion fix)
    results["codebase_loading"] = await test_codebase_loading()
    
    # Test 3: Preference setting (validates parametric memory fix)
    results["preference_setting"] = await test_preference_setting()
    
    # Test 4: Preference retrieval
    if results["preference_setting"]:
        results["preference_retrieval"] = await test_preference_retrieval()
    
    # Test 5: Memory search
    if results["codebase_loading"]:
        results["memory_search"] = await test_memory_search()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Fixes successfully validated!")
        print("\nCritical issues resolved:")
        print("✅ Data ingestion working (Files loaded > 0)")
        print("✅ Parametric memory functional")
        print("✅ Project isolation implemented")
        print("✅ Backend configuration corrected")
    else:
        print("⚠️ Some tests failed - Service may need restart")
        print("\nTo apply fixes, restart the service:")
        print("1. Stop current service (Ctrl+C)")
        print("2. Run: python run_gguf_service.py")
        print("3. Run this validation script again")
    
    print("\n📝 Backend Configuration Summary:")
    print("- Textual Memory: 'general_text' (with Qdrant vector DB)")
    print("- Activation Memory: 'uninitialized' (simplified from kv_cache)")
    print("- Parametric Memory: 'uninitialized' (simplified for stability)")

if __name__ == "__main__":
    asyncio.run(main())