#!/usr/bin/env python3
"""
Test Script for STRING.MD Preferences Integration

This script validates that the STRING.MD preferences system is working correctly
and that it has properly replaced the JSON preferences in MemOS and agent orchestration.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_loader():
    """Test that config_loader correctly loads STRING.MD preferences."""
    print("🔬 Testing Config Loader...")
    
    try:
        from config_loader import ConfigLoader
        
        # Initialize config loader
        loader = ConfigLoader("config.yaml")
        config = loader.load()
        
        # Check if preferences are loaded
        preferences = config.get('preferences', {})
        content = preferences.get('content', '')
        source = preferences.get('source', '')
        pref_type = preferences.get('type', '')
        
        print(f"  ✅ Config loaded successfully")
        print(f"  📄 Preferences source: {source}")
        print(f"  📝 Preferences type: {pref_type}")
        print(f"  📊 Content length: {len(content)} characters")
        
        if content:
            print(f"  📋 Preview: {content[:100]}...")
            return True
        else:
            print(f"  ⚠️ No preferences content found")
            return False
            
    except Exception as e:
        print(f"  ❌ Config loader test failed: {e}")
        return False


def test_project_memory_manager():
    """Test that ProjectMemoryManager can retrieve STRING.MD preferences."""
    print("\n🧠 Testing Project Memory Manager...")
    
    try:
        from project_memory_manager import ProjectMemoryManager
        
        # Initialize project memory manager
        pm_manager = ProjectMemoryManager()
        
        # Test STRING.MD preferences retrieval
        user_id = "test_user"
        project_id = "test_project"
        
        # Get raw markdown preferences
        markdown_prefs = pm_manager.get_string_md_preferences(user_id, project_id)
        print(f"  ✅ ProjectMemoryManager initialized")
        print(f"  📋 Retrieved markdown preferences: {len(markdown_prefs)} characters")
        
        if markdown_prefs:
            print(f"  📝 Preview: {markdown_prefs[:100]}...")
            
            # Test formatted preferences for prompt
            formatted_prefs = pm_manager.format_preferences_for_prompt(user_id, project_id)
            print(f"  🎯 Formatted for prompt: {len(formatted_prefs)} characters")
            
            if formatted_prefs:
                print(f"  📄 Formatted preview: {formatted_prefs[:150]}...")
                return True
        else:
            print(f"  ⚠️ No markdown preferences retrieved")
            return False
            
    except Exception as e:
        print(f"  ❌ Project memory manager test failed: {e}")
        return False


def test_orchestrator_integration():
    """Test that the orchestrator can use markdown preferences."""
    print("\n🎭 Testing Orchestrator Integration...")
    
    try:
        # Import and initialize orchestrator components
        from agents.orchestrator import ProjectManager
        from agents.base import Task
        from uuid import uuid4
        
        # Create a test task with proper UUID
        test_task = Task(
            task_id=uuid4(),  # Generate proper UUID
            prompt="Create a simple Python function for testing",
            context={
                'user_id': 'test_user',
                'project_id': 'test_project',
                'agent_role': 'code_generator'  # Move agent_role to context
            }
        )
        
        # Initialize project manager (this will test the integration)
        print(f"  ⚙️ Initializing ProjectManager...")
        pm = ProjectManager("localhost", 8000)
        
        # Test context enrichment (this should load STRING.MD preferences)
        if hasattr(pm, 'project_memory_manager') and pm.project_memory_manager:
            # Simulate context enrichment
            try:
                markdown_prefs = pm.project_memory_manager.get_string_md_preferences(
                    test_task.context['user_id'], 
                    test_task.context['project_id']
                )
                
                if markdown_prefs:
                    print(f"  ✅ Orchestrator can access STRING.MD preferences")
                    print(f"  📋 Retrieved {len(markdown_prefs)} characters")
                    
                    # Test formatted context
                    formatted = pm.project_memory_manager.format_preferences_for_prompt(
                        test_task.context['user_id'], 
                        test_task.context['project_id']
                    )
                    
                    if formatted:
                        print(f"  🎯 Context formatting successful: {len(formatted)} characters")
                        return True
                else:
                    print(f"  ⚠️ No preferences found in orchestrator")
                    return False
                    
            except Exception as e:
                print(f"  ❌ Context enrichment failed: {e}")
                return False
        else:
            print(f"  ⚠️ ProjectMemoryManager not available in orchestrator")
            return False
            
    except Exception as e:
        print(f"  ❌ Orchestrator integration test failed: {e}")
        return False


def test_string_md_file():
    """Test that STRING.MD file exists and is readable."""
    print("\n📄 Testing STRING.MD File...")
    
    string_md_path = project_root / "STRING.MD"
    
    try:
        if string_md_path.exists():
            with open(string_md_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            print(f"  ✅ STRING.MD file found")
            print(f"  📊 File size: {len(content)} characters")
            print(f"  📝 First line: {content.split(chr(10))[0] if content else 'Empty'}")
            
            # Check for key sections
            if "Project Context" in content or "Preferences" in content:
                print(f"  🎯 Contains project context/preferences")
                return True
            else:
                print(f"  ⚠️ File exists but may not contain preferences")
                return False
        else:
            print(f"  ❌ STRING.MD file not found at {string_md_path}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading STRING.MD: {e}")
        return False


def test_legacy_json_fallback():
    """Test that legacy JSON preferences still work as fallback."""
    print("\n🔄 Testing Legacy JSON Fallback...")
    
    try:
        from project_memory_manager import ProjectMemoryManager
        
        pm_manager = ProjectMemoryManager()
        user_id = "test_user"
        project_id = "test_project"
        
        # Test legacy JSON preferences
        legacy_prefs = pm_manager.get_project_preferences(user_id, project_id)
        
        print(f"  ✅ Legacy preferences method accessible")
        print(f"  📊 Legacy preferences count: {len(legacy_prefs) if legacy_prefs else 0}")
        
        if legacy_prefs:
            print(f"  📋 Legacy preferences available as fallback")
        else:
            print(f"  ℹ️ No legacy preferences (expected with new system)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Legacy fallback test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🧪 STRING.MD Preferences Validation")
    print("=" * 50)
    
    tests = [
        ("STRING.MD File", test_string_md_file),
        ("Config Loader", test_config_loader),
        ("Project Memory Manager", test_project_memory_manager),
        ("Orchestrator Integration", test_orchestrator_integration),
        ("Legacy JSON Fallback", test_legacy_json_fallback),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! STRING.MD preferences system is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)