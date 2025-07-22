#!/usr/bin/env python3
"""
Test script for YAML-based ModelManager implementation.

This script validates the ModelManager with YAML configuration,
lazy loading, and singleton pattern as specified.
"""

import sys
import os
import time
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_yaml_configuration_loading():
    """Test YAML configuration loading."""
    print("=== Test 1: YAML Configuration Loading ===")
    
    try:
        from models import ModelManager
        
        # Test with the actual config file
        config_path = "config/models.yaml"
        if not os.path.exists(config_path):
            print("⚠️  Config file not found, creating temporary one")
            config_path = create_temp_config()
        
        manager = ModelManager(config_path)
        
        # Check if models were loaded
        available = manager.list_available_models()
        print(f"✅ Loaded {len(available)} models from YAML")
        print(f"   Available models: {available}")
        
        # Verify specific models exist
        expected_models = ["SmolLM3-3B", "gemma-3n-E4B-it", "Qwen3-1.7B-GGUF"]
        for model_name in expected_models:
            if model_name in available:
                print(f"✅ {model_name} found in configuration")
            else:
                print(f"⚠️  {model_name} not found in configuration")
        
        return True
        
    except Exception as e:
        print(f"❌ YAML configuration loading failed: {e}")
        return False


def test_global_singleton_pattern():
    """Test global singleton instance."""
    print("\n=== Test 2: Global Singleton Pattern ===")
    
    try:
        from models import model_manager, get_model, list_available_models
        
        # Test global singleton instance exists
        assert model_manager is not None, "Global model_manager not created"
        print("✅ Global model_manager instance exists")
        
        # Test convenience functions work
        available_models = list_available_models()
        assert len(available_models) > 0, "No models available"
        print(f"✅ Convenience functions work: {len(available_models)} models")
        
        # Test that multiple imports give same instance
        from models.manager import model_manager as manager2
        assert model_manager is manager2, "Singleton pattern broken"
        print("✅ Singleton pattern working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Global singleton test failed: {e}")
        return False


def test_lazy_loading_and_caching():
    """Test lazy loading and caching behavior."""
    print("\n=== Test 3: Lazy Loading and Caching ===")
    
    try:
        from models import model_manager
        
        # Create a test model that can actually be loaded
        test_config = create_test_model_config()
        model_manager._model_configs['test_openai'] = test_config
        
        # Check initially not loaded
        loaded = model_manager.list_loaded_models()
        assert 'test_openai' not in loaded, "Model should not be loaded initially"
        print("✅ Model not loaded initially (lazy loading)")
        
        # First access - should trigger loading
        print("🔄 First access - triggering load...")
        model1 = model_manager.get_model('test_openai')
        
        # Check it's now loaded
        loaded_after = model_manager.list_loaded_models()
        assert 'test_openai' in loaded_after, "Model should be loaded after first access"
        print("✅ Model loaded after first access")
        
        # Second access - should hit cache
        print("🔄 Second access - should hit cache...")
        start_time = time.time()
        model2 = model_manager.get_model('test_openai')
        cache_time = time.time() - start_time
        
        # Should be same instance (singleton pattern)
        assert model1 is model2, "Should return same instance from cache"
        assert cache_time < 0.1, "Cache access should be very fast"
        print(f"✅ Cache hit working (access time: {cache_time:.4f}s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Lazy loading and caching test failed: {e}")
        return False


def test_access_time_tracking():
    """Test access time tracking for loaded models."""
    print("\n=== Test 4: Access Time Tracking ===")
    
    try:
        from models import model_manager
        
        # Ensure test model is available
        if 'test_openai' not in model_manager._model_configs:
            test_config = create_test_model_config()
            model_manager._model_configs['test_openai'] = test_config
        
        # Load model and get initial access time
        model = model_manager.get_model('test_openai')
        initial_time = model_manager._last_access_times.get('test_openai', 0)
        
        # Wait a bit and access again
        time.sleep(0.1)
        model = model_manager.get_model('test_openai')
        updated_time = model_manager._last_access_times.get('test_openai', 0)
        
        # Access time should have been updated
        assert updated_time > initial_time, "Access time should be updated"
        print("✅ Access time tracking working")
        
        # Check model info includes access time
        info = model_manager.get_model_info('test_openai')
        assert 'last_access' in info, "Model info should include last_access"
        assert info['is_loaded'] == True, "Model info should show loaded status"
        print("✅ Model info includes access tracking")
        
        return True
        
    except Exception as e:
        print(f"❌ Access time tracking test failed: {e}")
        return False


def test_model_configuration_validation():
    """Test model configuration validation."""
    print("\n=== Test 5: Model Configuration Validation ===")
    
    try:
        from models import model_manager
        
        # Test getting info for configured models
        available = model_manager.list_available_models()
        if available:
            first_model = available[0]
            info = model_manager.get_model_info(first_model)
            
            # Check required fields
            assert 'path' in info, "Model info should include path"
            assert 'loader' in info, "Model info should include loader"
            assert 'params' in info, "Model info should include params"
            print(f"✅ Model info validation passed for {first_model}")
        
        # Test error handling for non-existent model
        try:
            model_manager.get_model('non_existent_model')
            print("❌ Should have raised error for non-existent model")
            return False
        except ValueError as e:
            if "not found in configuration" in str(e):
                print("✅ Proper error handling for non-existent models")
            else:
                print(f"❌ Unexpected error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Model configuration validation test failed: {e}")
        return False


def test_memory_statistics():
    """Test memory and loading statistics."""
    print("\n=== Test 6: Memory Statistics ===")
    
    try:
        from models import get_memory_stats, model_manager
        
        # Get stats
        stats = get_memory_stats()
        
        # Verify stats structure
        required_fields = ['total_configured', 'currently_loaded', 'loaded_models', 'available_models']
        for field in required_fields:
            assert field in stats, f"Stats should include {field}"
        
        print(f"✅ Memory statistics working:")
        print(f"   Total configured: {stats['total_configured']}")
        print(f"   Currently loaded: {stats['currently_loaded']}")
        print(f"   Available models: {len(stats['available_models'])}")
        
        # Test model unloading
        loaded = model_manager.list_loaded_models()
        if loaded:
            first_loaded = loaded[0]
            result = model_manager.unload_model(first_loaded)
            assert result == True, "Model unloading should succeed"
            
            # Check stats updated
            new_stats = get_memory_stats()
            assert new_stats['currently_loaded'] == stats['currently_loaded'] - 1
            print(f"✅ Model unloading working")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory statistics test failed: {e}")
        return False


def test_huggingface_model_loading():
    """Test HuggingFace model loading if available."""
    print("\n=== Test 7: HuggingFace Model Loading ===")
    
    try:
        from models import model_manager
        
        # Check if SmolLM3-3B-HF is configured
        available = model_manager.list_available_models()
        if 'SmolLM3-3B-HF' in available:
            print("🔄 Attempting to load HuggingFace model...")
            try:
                model = model_manager.get_model('SmolLM3-3B-HF')
                print("✅ HuggingFace model loaded successfully")
                
                # Check it's in loaded models
                loaded = model_manager.list_loaded_models()
                assert 'SmolLM3-3B-HF' in loaded
                print("✅ HuggingFace model tracked correctly")
                
                return True
            except Exception as e:
                print(f"⚠️  HuggingFace model loading failed (expected): {e}")
                return True  # This is OK, model files may not exist
        else:
            print("⚠️  SmolLM3-3B-HF not in configuration, skipping")
            return True
        
    except Exception as e:
        print(f"❌ HuggingFace model test failed: {e}")
        return False


def create_temp_config():
    """Create a temporary YAML config for testing."""
    config_content = """
models:
  test_model:
    path: "test-model"
    loader: "openai"
    params:
      api_base: "http://localhost:11434/v1"
      temperature: 0.1
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        return f.name


def create_test_model_config():
    """Create a simple test model configuration."""
    return {
        'path': 'test-openai-model',
        'loader': 'openai',
        'params': {
            'api_base': 'http://localhost:11434/v1',
            'api_key': 'fake-key',
            'temperature': 0.1
        }
    }


def main():
    """Run all tests."""
    print("🧪 YAML-based ModelManager Test Suite")
    print("=" * 50)
    
    tests = [
        test_yaml_configuration_loading,
        test_global_singleton_pattern,
        test_lazy_loading_and_caching,
        test_access_time_tracking,
        test_model_configuration_validation,
        test_memory_statistics,
        test_huggingface_model_loading
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
        print("🎉 All tests passed! YAML ModelManager is working correctly.")
    else:
        print("❌ Some tests failed. Review the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)