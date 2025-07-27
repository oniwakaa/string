#!/usr/bin/env python3
"""
Simple STRING.MD Preferences Validation

Quick validation that STRING.MD preferences are working correctly.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Simple validation of STRING.MD preferences system."""
    print("🧪 STRING.MD Preferences - Quick Validation")
    print("=" * 50)
    
    # Test 1: Check STRING.MD file exists
    string_md_path = project_root / "STRING.MD"
    if not string_md_path.exists():
        print("❌ STRING.MD file not found!")
        return False
    
    print("✅ STRING.MD file found")
    
    # Test 2: Check config loader can read it
    try:
        from config_loader import ConfigLoader
        loader = ConfigLoader("config.yaml")
        config = loader.load()
        
        preferences = config.get('preferences', {})
        content = preferences.get('content', '')
        
        if content:
            print(f"✅ Config loader working: {len(content)} characters loaded")
        else:
            print("❌ Config loader not loading STRING.MD content")
            return False
            
    except Exception as e:
        print(f"❌ Config loader failed: {e}")
        return False
    
    # Test 3: Check project memory manager integration
    try:
        from project_memory_manager import ProjectMemoryManager
        pm = ProjectMemoryManager()
        
        markdown_prefs = pm.get_string_md_preferences("test_user", "test_project")
        if markdown_prefs:
            print(f"✅ ProjectMemoryManager working: {len(markdown_prefs)} characters")
        else:
            print("❌ ProjectMemoryManager not retrieving STRING.MD")
            return False
            
        # Test formatting
        formatted = pm.format_preferences_for_prompt("test_user", "test_project")
        if formatted:
            print(f"✅ Preference formatting working: {len(formatted)} characters")
        else:
            print("❌ Preference formatting failed")
            return False
            
    except Exception as e:
        print(f"❌ ProjectMemoryManager failed: {e}")
        return False
    
    print("\n🎉 All core STRING.MD functionality is working!")
    print("\n📋 STRING.MD Content Preview:")
    print("-" * 50)
    print(content[:300] + "..." if len(content) > 300 else content)
    print("-" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)