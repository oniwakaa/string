#!/usr/bin/env python3
"""
Debug script to test project memory manager functionality directly
"""

import sys
import os

# Add MemOS to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MemOS', 'src'))

try:
    from project_memory_manager import ProjectMemoryManager
    from memos.mem_os.main import MOS
    from memos.configs.mem_os import MOSConfig
    
    print("✅ Imports successful")
    
    # Test project memory manager initialization
    pm = ProjectMemoryManager()
    print(f"✅ ProjectMemoryManager created: {pm}")
    print(f"📊 MemOS instance available: {pm.mos_instance is not None}")
    
    # Test cube ID generation
    user_id = "debug_user"
    project_id = "debug_project"
    cube_id = pm._generate_project_cube_id(user_id, project_id)
    print(f"📊 Generated cube ID: {cube_id}")
    
    # Test if we can create a MemOS instance (minimal config)
    try:
        mos_config = MOSConfig(
            user_id=user_id,
            session_id="debug_session",
            enable_textual_memory=True,
            enable_activation_memory=False,
            top_k=3
        )
        mos = MOS(mos_config)
        print(f"✅ MemOS instance created: {mos}")
        
        # Set MemOS instance on project manager
        pm.set_mos_instance(mos)
        print(f"✅ MemOS instance set on ProjectMemoryManager")
        
        # Test cube creation
        print(f"🔧 Testing cube creation for {user_id}:{project_id}")
        success = pm.create_project_cube(user_id, project_id)
        print(f"📊 Cube creation result: {success}")
        
        if success:
            # Test preference setting
            print(f"🔧 Testing preference setting")
            pref_success = pm.add_project_preference(
                user_id=user_id,
                project_id=project_id,
                category="test",
                key="debug_test",
                value="test_value",
                description="Debug test preference"
            )
            print(f"📊 Preference setting result: {pref_success}")
            
            # Test preference retrieval
            prefs = pm.get_project_preferences(user_id, project_id)
            print(f"📊 Retrieved preferences: {prefs}")
        
    except Exception as e:
        print(f"❌ MemOS creation failed: {e}")
        import traceback
        traceback.print_exc()
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()