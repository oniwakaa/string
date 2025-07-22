#!/usr/bin/env python3
"""
Test script to validate MemOS GeneralMemCubeConfig with corrected schema.
This script tests the configuration incrementally to isolate any issues.
"""

import sys
import os
import tempfile

# Add MemOS to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MemOS', 'src'))

def test_basic_imports():
    """Test 1: Basic imports"""
    print("=== Test 1: Basic Imports ===")
    try:
        from memos.configs.mem_cube import GeneralMemCubeConfig
        from memos.mem_cube.general import GeneralMemCube
        print("✅ Basic imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_textual_only_config():
    """Test 2: Textual memory only configuration"""
    print("\n=== Test 2: Textual Memory Only Config ===")
    try:
        from memos.configs.mem_cube import GeneralMemCubeConfig
        
        # Minimal textual memory config
        config = GeneralMemCubeConfig(
            user_id="test_user",
            cube_id="test_cube", 
            text_mem={
                "backend": "general_text",
                "config": {
                    "embedder": {
                        "backend": "sentence_transformer",
                        "config": {
                            "model_name_or_path": "all-MiniLM-L6-v2",
                            "trust_remote_code": True
                        }
                    },
                    "vector_db": {
                        "backend": "qdrant",
                        "config": {
                            "collection_name": "test_collection",
                            "vector_dimension": 384,
                            "distance_metric": "cosine",
                            "host": None,
                            "port": None,
                            "path": "./test_qdrant"
                        }
                    },
                    "extractor_llm": {
                        "backend": "openai",
                        "config": {
                            "model_name_or_path": "gpt-3.5-turbo",
                            "temperature": 0.0,
                            "max_tokens": 8192,
                            "api_key": "fake-api-key",
                            "api_base": "http://localhost:11434/v1"
                        }
                    }
                }
            },
            act_mem={
                "backend": "uninitialized",
                "config": {}
            },
            para_mem={
                "backend": "uninitialized", 
                "config": {}
            }
        )
        print("✅ Textual-only config validation passed")
        return True
    except Exception as e:
        print(f"❌ Textual-only config failed: {e}")
        return False

def test_activation_memory_config():
    """Test 3: Add activation memory configuration"""
    print("\n=== Test 3: Activation Memory Config ===")
    try:
        from memos.configs.mem_cube import GeneralMemCubeConfig
        
        config = GeneralMemCubeConfig(
            user_id="test_user",
            cube_id="test_cube",
            text_mem={
                "backend": "general_text",
                "config": {
                    "embedder": {
                        "backend": "sentence_transformer",
                        "config": {
                            "model_name_or_path": "all-MiniLM-L6-v2",
                            "trust_remote_code": True
                        }
                    },
                    "vector_db": {
                        "backend": "qdrant",
                        "config": {
                            "collection_name": "test_collection",
                            "vector_dimension": 384,
                            "distance_metric": "cosine",
                            "host": None,
                            "port": None,
                            "path": "./test_qdrant"
                        }
                    },
                    "extractor_llm": {
                        "backend": "openai",
                        "config": {
                            "model_name_or_path": "gpt-3.5-turbo",
                            "temperature": 0.0,
                            "max_tokens": 8192,
                            "api_key": "fake-api-key",
                            "api_base": "http://localhost:11434/v1"
                        }
                    }
                }
            },
            act_mem={
                "backend": "kv_cache",
                "config": {
                    "memory_filename": "activation_cache.pkl",
                    "extractor_llm": {
                        "backend": "huggingface",
                        "config": {
                            "model_name_or_path": "SmolLM3-3B",
                            "temperature": 0.0,
                            "max_tokens": 16384
                        }
                    }
                }
            },
            para_mem={
                "backend": "uninitialized",
                "config": {}
            }
        )
        print("✅ Activation memory config validation passed")
        return True
    except Exception as e:
        print(f"❌ Activation memory config failed: {e}")
        return False

def test_full_config():
    """Test 4: Full configuration with all memory types"""
    print("\n=== Test 4: Full Config with All Memory Types ===")
    try:
        from memos.configs.mem_cube import GeneralMemCubeConfig
        
        config = GeneralMemCubeConfig(
            user_id="test_user",
            cube_id="test_cube",
            text_mem={
                "backend": "general_text",
                "config": {
                    "embedder": {
                        "backend": "sentence_transformer",
                        "config": {
                            "model_name_or_path": "all-MiniLM-L6-v2",
                            "trust_remote_code": True
                        }
                    },
                    "vector_db": {
                        "backend": "qdrant",
                        "config": {
                            "collection_name": "test_collection",
                            "vector_dimension": 384,
                            "distance_metric": "cosine",
                            "host": None,
                            "port": None,
                            "path": "./test_qdrant"
                        }
                    },
                    "extractor_llm": {
                        "backend": "openai",
                        "config": {
                            "model_name_or_path": "gpt-3.5-turbo",
                            "temperature": 0.0,
                            "max_tokens": 8192,
                            "api_key": "fake-api-key",
                            "api_base": "http://localhost:11434/v1"
                        }
                    }
                }
            },
            act_mem={
                "backend": "kv_cache",
                "config": {
                    "memory_filename": "activation_cache.pkl",
                    "extractor_llm": {
                        "backend": "huggingface",
                        "config": {
                            "model_name_or_path": "SmolLM3-3B",
                            "temperature": 0.0,
                            "max_tokens": 16384
                        }
                    }
                }
            },
            para_mem={
                "backend": "lora",
                "config": {
                    "memory_filename": "parametric_memory.adapter",
                    "extractor_llm": {
                        "backend": "huggingface",
                        "config": {
                            "model_name_or_path": "SmolLM3-3B",
                            "temperature": 0.0,
                            "max_tokens": 16384
                        }
                    }
                }
            }
        )
        print("✅ Full config validation passed")
        return True
    except Exception as e:
        print(f"❌ Full config failed: {e}")
        return False

def test_memcube_creation():
    """Test 5: Actual MemCube creation"""
    print("\n=== Test 5: MemCube Creation ===")
    try:
        from memos.configs.mem_cube import GeneralMemCubeConfig
        from memos.mem_cube.general import GeneralMemCube
        
        config = GeneralMemCubeConfig(
            user_id="test_user",
            cube_id="test_cube",
            text_mem={
                "backend": "general_text",
                "config": {
                    "embedder": {
                        "backend": "sentence_transformer",
                        "config": {
                            "model_name_or_path": "all-MiniLM-L6-v2",
                            "trust_remote_code": True
                        }
                    },
                    "vector_db": {
                        "backend": "qdrant",
                        "config": {
                            "collection_name": "test_collection",
                            "vector_dimension": 384,
                            "distance_metric": "cosine",
                            "host": None,
                            "port": None,
                            "path": "./test_qdrant"
                        }
                    },
                    "extractor_llm": {
                        "backend": "openai",
                        "config": {
                            "model_name_or_path": "gpt-3.5-turbo",
                            "temperature": 0.0,
                            "max_tokens": 8192,
                            "api_key": "fake-api-key",
                            "api_base": "http://localhost:11434/v1"
                        }
                    }
                }
            },
            act_mem={
                "backend": "uninitialized",
                "config": {}
            },
            para_mem={
                "backend": "uninitialized",
                "config": {}
            }
        )
        
        # Try creating the MemCube (may fail due to missing dependencies, but schema should be OK)
        mem_cube = GeneralMemCube(config)
        print("✅ MemCube creation successful (basic initialization)")
        return True
    except Exception as e:
        print(f"⚠️  MemCube creation failed (expected due to dependencies): {e}")
        return False  # This is expected to fail but config should be valid

def main():
    """Run all tests"""
    print("🧪 MemOS Configuration Validation Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_textual_only_config, 
        test_activation_memory_config,
        test_full_config,
        test_memcube_creation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print(f"\n🏁 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results[:4]):  # First 4 tests should pass
        print("✅ Configuration schema is correct!")
    else:
        print("❌ Configuration schema has issues")
    
    return all(results[:4])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)