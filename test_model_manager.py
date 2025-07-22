#!/usr/bin/env python3
"""
Test script for the centralized ModelManager.

This script validates the ModelManager implementation and demonstrates
its key features including loading, sharing, memory management, and eviction.
"""

import sys
import os
import time
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_model_manager_basic():
    """Test basic ModelManager functionality."""
    print("=== Test 1: Basic ModelManager Functionality ===")
    
    try:
        from models import ModelManager, ModelConfig, get_model_manager
        
        # Test singleton pattern
        manager1 = ModelManager()
        manager2 = get_model_manager()
        assert manager1 is manager2, "Singleton pattern failed"
        print("✅ Singleton pattern working")
        
        # Test model configuration
        config = ModelConfig(
            name="test_model",
            type="openai",
            path="test-model",
            context_length=8192,
            parameters={"temperature": 0.01},
            memory_priority=1,
            max_idle_time=300
        )
        
        manager1.add_model_config(config)
        print("✅ Model configuration added")
        
        # Test model listing
        available = manager1.list_available_models()
        assert "test_model" in available, "Model not in available list"
        print("✅ Model appears in available list")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading from JSON."""
    print("\n=== Test 2: Configuration Loading ===")
    
    try:
        from models import get_model_manager
        
        # Create temporary config file
        test_config = {
            "max_memory_mb": 4096,
            "models": [
                {
                    "name": "test_openai",
                    "type": "openai",
                    "path": "gpt-3.5-turbo",
                    "context_length": 4096,
                    "parameters": {"temperature": 0.1},
                    "memory_priority": 1,
                    "max_idle_time": 300,
                    "preload": False
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = get_model_manager()
            manager.load_config(config_path)
            
            # Verify config was loaded
            available = manager.list_available_models()
            assert "test_openai" in available, "Config model not loaded"
            print("✅ Configuration loaded from JSON")
            
            # Test memory limit
            memory_info = manager.get_memory_usage()
            assert memory_info['limit_mb'] == 4096, "Memory limit not set correctly"
            print("✅ Memory limit configured correctly")
            
            return True
            
        finally:
            os.unlink(config_path)
        
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False


def test_model_loading():
    """Test model loading and caching."""
    print("\n=== Test 3: Model Loading and Caching ===")
    
    try:
        from models import get_model_manager, ModelConfig
        
        manager = get_model_manager()
        
        # Add a simple test model (OpenAI type for easy testing)
        config = ModelConfig(
            name="simple_test",
            type="openai",
            path="test-model",
            context_length=2048,
            parameters={"api_base": "http://localhost:11434/v1"},
            memory_priority=1,
            max_idle_time=60
        )
        manager.add_model_config(config)
        
        # Test model loading
        model1 = manager.get_model("simple_test")
        assert model1 is not None, "Model not loaded"
        print("✅ Model loaded successfully")
        
        # Test caching (should return same instance)
        model2 = manager.get_model("simple_test")
        assert model1 is model2, "Model not cached properly"
        print("✅ Model caching working")
        
        # Check loaded models list
        loaded = manager.list_loaded_models()
        assert "simple_test" in loaded, "Model not in loaded list"
        print("✅ Loaded models tracking working")
        
        return True
        
    except Exception as e:
        print(f"❌ Model loading test failed: {e}")
        return False


def test_memory_management():
    """Test memory management and statistics."""
    print("\n=== Test 4: Memory Management ===")
    
    try:
        from models import get_model_manager
        
        manager = get_model_manager()
        
        # Get memory usage
        memory_info = manager.get_memory_usage()
        assert 'total_mb' in memory_info, "Memory info missing total_mb"
        assert 'loaded_models' in memory_info, "Memory info missing loaded_models"
        print("✅ Memory usage reporting working")
        
        # Get model statistics
        stats = manager.get_model_stats()
        print(f"✅ Model statistics available: {len(stats)} models tracked")
        
        # Test memory limit setting
        original_limit = memory_info['limit_mb']
        manager.set_memory_limit(1024)
        new_memory_info = manager.get_memory_usage()
        assert new_memory_info['limit_mb'] == 1024, "Memory limit not updated"
        
        # Restore original limit
        manager.set_memory_limit(original_limit)
        print("✅ Memory limit setting working")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory management test failed: {e}")
        return False


def test_model_eviction():
    """Test model eviction functionality."""
    print("\n=== Test 5: Model Eviction ===")
    
    try:
        from models import get_model_manager, ModelConfig
        
        manager = get_model_manager()
        
        # Add a test model with short idle time
        config = ModelConfig(
            name="eviction_test",
            type="openai",
            path="test-eviction",
            context_length=1024,
            parameters={},
            memory_priority=5,  # Low priority
            max_idle_time=1  # Very short idle time
        )
        manager.add_model_config(config)
        
        # Load the model
        model = manager.get_model("eviction_test")
        assert "eviction_test" in manager.list_loaded_models()
        print("✅ Test model loaded")
        
        # Wait longer than idle time
        time.sleep(2)
        
        # Test manual unload
        result = manager.unload_model("eviction_test", force=True)
        assert result is True, "Manual unload failed"
        assert "eviction_test" not in manager.list_loaded_models()
        print("✅ Manual model unloading working")
        
        return True
        
    except Exception as e:
        print(f"❌ Model eviction test failed: {e}")
        return False


def test_integration_helpers():
    """Test integration helper functions."""
    print("\n=== Test 6: Integration Helpers ===")
    
    try:
        from models.integration import get_llm_for_memos, ModelManagerAdapter
        
        # Test MemOS LLM config generation
        llm_config = get_llm_for_memos(backend="openai", model_path="test-model")
        assert 'backend' in llm_config, "LLM config missing backend"
        assert 'config' in llm_config, "LLM config missing config"
        print("✅ MemOS LLM config generation working")
        
        # Test adapter creation
        adapter = ModelManagerAdapter("TestAgent")
        assert adapter.agent_name == "TestAgent", "Adapter not configured correctly"
        
        memory_info = adapter.get_memory_usage()
        assert 'total_mb' in memory_info, "Adapter memory info not working"
        print("✅ ModelManagerAdapter working")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration helpers test failed: {e}")
        return False


def test_real_config():
    """Test with the actual configuration file."""
    print("\n=== Test 7: Real Configuration ===")
    
    try:
        from models import get_model_manager
        
        config_path = "src/models/config.json"
        if not os.path.exists(config_path):
            print("⚠️  Real config file not found, skipping test")
            return True
        
        manager = get_model_manager()
        manager.load_config(config_path)
        
        available = manager.list_available_models()
        expected_models = ["SmolLM3-3B", "SmolLM3-3B-GGUF", "CodeGenerator-Gemma", 
                          "QualityLLM-Qwen", "WebScraper-Local"]
        
        for model_name in expected_models:
            assert model_name in available, f"Expected model {model_name} not found"
        
        print(f"✅ Real configuration loaded: {len(available)} models available")
        
        # Test loading a simple model (OpenAI type)
        if "WebScraper-Local" in available:
            model = manager.get_model("WebScraper-Local")
            assert model is not None, "OpenAI model not loaded"
            print("✅ OpenAI-type model loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Real configuration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 ModelManager Test Suite")
    print("=" * 50)
    
    tests = [
        test_model_manager_basic,
        test_config_loading,
        test_model_loading,
        test_memory_management,
        test_model_eviction,
        test_integration_helpers,
        test_real_config
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
    
    print(f"\n🏁 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! ModelManager is ready for integration.")
    else:
        print("❌ Some tests failed. Review the implementation.")
    
    # Cleanup
    try:
        from models import get_model_manager
        manager = get_model_manager()
        manager.shutdown()
        print("✅ ModelManager shutdown complete")
    except:
        pass
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)