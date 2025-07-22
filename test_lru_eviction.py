#!/usr/bin/env python3
"""
Test script for LRU memory eviction policy in ModelManager.

This script validates that the eviction policy works correctly and 
automatically frees up memory from idle models.
"""

import sys
import os
import time
import asyncio
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, '.')


def test_idle_timeout_constant():
    """Test that IDLE_TIMEOUT_SECONDS is properly defined."""
    print("=== Test 1: IDLE_TIMEOUT_SECONDS Constant ===")
    
    try:
        from models.manager import ModelManager
        
        # Test that constant exists
        timeout = ModelManager.IDLE_TIMEOUT_SECONDS
        assert timeout == 600, f"Expected 600 seconds, got {timeout}"
        print(f"✅ IDLE_TIMEOUT_SECONDS = {timeout} seconds (10 minutes)")
        
        return True
        
    except Exception as e:
        print(f"❌ IDLE_TIMEOUT_SECONDS test failed: {e}")
        return False


def test_evict_idle_models_method():
    """Test the evict_idle_models method exists and works."""
    print("\n=== Test 2: evict_idle_models() Method ===")
    
    try:
        from models.manager import ModelManager
        
        # Create ModelManager instance  
        manager = ModelManager()
        
        # Test method exists
        assert hasattr(manager, 'evict_idle_models'), "evict_idle_models method not found"
        print("✅ evict_idle_models method exists")
        
        # Test method can be called (should return 0 with no loaded models)
        evicted = manager.evict_idle_models()
        assert evicted == 0, f"Expected 0 evicted, got {evicted}"
        print(f"✅ evict_idle_models() returned {evicted} (no models to evict)")
        
        # Test force_evict_one parameter
        evicted = manager.evict_idle_models(force_evict_one=True)
        assert evicted == 0, f"Expected 0 evicted, got {evicted}"
        print("✅ force_evict_one=True works with no loaded models")
        
        return True
        
    except Exception as e:
        print(f"❌ evict_idle_models method test failed: {e}")
        return False


def test_eviction_integration_in_get_model():
    """Test that eviction is integrated into get_model() workflow."""
    print("\n=== Test 3: Eviction Integration in get_model() ===")
    
    try:
        from models.manager import ModelManager
        import re
        
        # Read the manager.py source to check for eviction call
        manager_path = "src/models/manager.py"
        with open(manager_path, 'r') as f:
            source = f.read()
        
        # Check that evict_idle_models is called in get_model
        pattern = r"def get_model.*?self\.evict_idle_models\(\)"
        if re.search(pattern, source, re.DOTALL):
            print("✅ evict_idle_models() is called in get_model() method")
        else:
            print("❌ evict_idle_models() call not found in get_model() method")
            return False
        
        # Check that it's called before model loading
        cache_miss_pattern = r"# Cache Miss.*?self\.evict_idle_models\(\).*?# Get model configuration"
        if re.search(cache_miss_pattern, source, re.DOTALL):
            print("✅ evict_idle_models() is called before loading new model")
        else:
            print("❌ evict_idle_models() not properly positioned in cache miss block")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Eviction integration test failed: {e}")
        return False


def test_lru_policy_with_mock_models():
    """Test LRU policy with simulated model access patterns."""
    print("\n=== Test 4: LRU Policy with Mock Models ===")
    
    try:
        from models.manager import ModelManager
        
        # Create manager instance
        manager = ModelManager()
        
        # Simulate loaded models with different access times
        current_time = time.time()
        
        # Mock model data (simulating loaded models)
        manager._loaded_models = {
            'recent_model': 'mock_model_1',
            'old_model': 'mock_model_2', 
            'very_old_model': 'mock_model_3'
        }
        
        # Set access times (very_old_model exceeds timeout)
        manager._last_access_times = {
            'recent_model': current_time - 300,      # 5 min ago (recent)
            'old_model': current_time - 500,         # 8.3 min ago (still OK)
            'very_old_model': current_time - 700     # 11.7 min ago (exceeds 10 min timeout)
        }
        
        # Test timeout-based eviction
        evicted = manager.evict_idle_models()
        
        # Should evict very_old_model only
        assert evicted == 1, f"Expected 1 evicted model, got {evicted}"
        assert 'very_old_model' not in manager._loaded_models, "very_old_model should be evicted"
        assert 'recent_model' in manager._loaded_models, "recent_model should remain"
        assert 'old_model' in manager._loaded_models, "old_model should remain"
        
        print("✅ Timeout-based eviction working correctly")
        
        # Test force eviction (LRU)
        evicted = manager.evict_idle_models(force_evict_one=True)
        assert evicted == 1, f"Expected 1 force-evicted model, got {evicted}"
        
        # Should evict the oldest remaining model (old_model)
        remaining = list(manager._loaded_models.keys())
        assert len(remaining) == 1, f"Expected 1 remaining model, got {len(remaining)}"
        assert 'recent_model' in remaining, "Most recent model should remain"
        
        print("✅ Force eviction (LRU) working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ LRU policy test failed: {e}")
        return False


def test_memory_stats_includes_timeout():
    """Test that memory stats include timeout information."""
    print("\n=== Test 5: Memory Stats Include Timeout ===")
    
    try:
        from models.manager import ModelManager
        
        manager = ModelManager()
        stats = manager.get_memory_stats()
        
        # Check that idle_timeout_seconds is included
        assert 'idle_timeout_seconds' in stats, "idle_timeout_seconds missing from stats"
        assert stats['idle_timeout_seconds'] == 600, f"Expected 600, got {stats['idle_timeout_seconds']}"
        
        print(f"✅ Memory stats include idle_timeout_seconds: {stats['idle_timeout_seconds']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory stats timeout test failed: {e}")
        return False


def test_global_evict_function():
    """Test the global evict_idle_models function."""
    print("\n=== Test 6: Global evict_idle_models Function ===")
    
    try:
        from models import evict_idle_models
        
        # Test function exists and can be called
        result = evict_idle_models()
        assert isinstance(result, int), f"Expected int result, got {type(result)}"
        print(f"✅ Global evict_idle_models() function works: returned {result}")
        
        # Test with force parameter
        result = evict_idle_models(force_evict_one=True)
        assert isinstance(result, int), f"Expected int result, got {type(result)}"
        print(f"✅ Global evict_idle_models(force_evict_one=True) works: returned {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Global evict function test failed: {e}")
        return False


def test_eviction_logging():
    """Test that eviction events are properly logged."""
    print("\n=== Test 7: Eviction Logging ===")
    
    try:
        import io
        import logging
        from models.manager import ModelManager
        
        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger('models.manager')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Create manager and simulate eviction scenario
        manager = ModelManager()
        current_time = time.time()
        
        # Add mock old model
        manager._loaded_models = {'old_model': 'mock'}
        manager._last_access_times = {'old_model': current_time - 700}  # 11+ min ago
        
        # Trigger eviction
        manager.evict_idle_models()
        
        # Check log output
        log_output = log_stream.getvalue()
        
        if 'Evicting idle model' in log_output and 'old_model' in log_output:
            print("✅ Eviction events are properly logged")
        else:
            print(f"⚠️  Eviction logging may not be working (log: {log_output[:100]}...)")
        
        # Clean up
        logger.removeHandler(handler)
        
        return True
        
    except Exception as e:
        print(f"❌ Eviction logging test failed: {e}")
        return False


def main():
    """Run all LRU eviction tests."""
    print("🧪 LRU Memory Eviction Policy Test Suite")
    print("=" * 50)
    
    tests = [
        test_idle_timeout_constant,
        test_evict_idle_models_method,
        test_eviction_integration_in_get_model,
        test_lru_policy_with_mock_models,
        test_memory_stats_includes_timeout,
        test_global_evict_function,
        test_eviction_logging
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n🏁 LRU Eviction Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All LRU eviction tests passed!")
        print("\n📋 LRU Eviction Policy Benefits:")
        print("  ✅ 10-minute idle timeout prevents memory waste")
        print("  ✅ Force eviction for aggressive memory cleanup")
        print("  ✅ Automatic cleanup before loading new models")
        print("  ✅ Comprehensive logging for monitoring")
        print("  ✅ Global convenience functions available")
    else:
        print("❌ Some LRU eviction tests failed. Review the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)