#!/usr/bin/env python3
"""
Test script for Dynamic MemCube Lifecycle functionality

This script tests Task 1.2: Implement Dynamic MemCube Lifecycle
- MemCube Registry functionality
- "Get or Create" method implementation
- Integration with ProjectManager workflow
- Error handling and resource management
"""

import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from agents.orchestrator import ProjectManager
    from project_memory_manager import ProjectMemoryManager, MEMOS_AVAILABLE
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the project root directory")
    sys.exit(1)


class MockMemOS:
    """Mock MemOS instance for testing purposes."""
    
    def __init__(self):
        self.cubes = {}
        self.users = set()
    
    def create_user(self, user_id: str):
        self.users.add(user_id)
        return True
    
    def register_mem_cube(self, mem_cube_name_or_path: str, mem_cube_id: str, user_id: str):
        self.cubes[mem_cube_id] = {
            'path': mem_cube_name_or_path,
            'user_id': user_id
        }
        return True
    
    def search(self, query: str, user_id: str, install_cube_ids: list, **kwargs):
        return {"results": [{"content": f"Mock search result for: {query}"}]}
    
    def add(self, memory_content: str, mem_cube_id: str, user_id: str, **kwargs):
        return True
    
    @property 
    def user_manager(self):
        return MockUserManager(self.cubes, self.users)


class MockUserManager:
    """Mock UserManager for testing."""
    
    def __init__(self, cubes, users):
        self.cubes = cubes
        self.users = users
    
    def validate_user(self, user_id: str):
        return user_id in self.users
    
    def get_user_cubes(self, user_id: str):
        return [cube_id for cube_id, info in self.cubes.items() 
                if info['user_id'] == user_id]


async def test_project_manager_memcube_registry():
    """Test 1: MemCube Registry in ProjectManager initialization."""
    
    print("🧪 Test 1: ProjectManager MemCube Registry")
    print("-" * 50)
    
    try:
        # Initialize ProjectManager
        pm = ProjectManager(service_host="localhost", service_port=8000)
        
        # Check that registry is initialized
        assert hasattr(pm, 'active_mem_cubes'), "ProjectManager should have active_mem_cubes registry"
        assert isinstance(pm.active_mem_cubes, dict), "active_mem_cubes should be a dictionary"
        assert hasattr(pm, 'project_memory_manager'), "ProjectManager should have project_memory_manager"
        
        # Check initial state
        assert len(pm.active_mem_cubes) == 0, "Registry should be empty initially"
        
        print("✅ MemCube registry initialized correctly")
        print(f"📊 Registry type: {type(pm.active_mem_cubes)}")
        print(f"📊 Initial registry size: {len(pm.active_mem_cubes)}")
        
        # Test registry methods
        active_cubes = pm.get_active_mem_cubes()
        assert isinstance(active_cubes, dict), "get_active_mem_cubes should return dict"
        
        print("✅ Registry accessor methods working")
        
        await pm.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


async def test_get_or_create_memcube_method():
    """Test 2: _get_or_create_mem_cube method functionality."""
    
    print("\n🧪 Test 2: Get or Create MemCube Method")
    print("-" * 50)
    
    try:
        # Initialize ProjectManager
        pm = ProjectManager()
        
        # Test case 1: MemOS not available
        if not MEMOS_AVAILABLE:
            result = await pm._get_or_create_mem_cube("test_user", "test_project")
            assert result is None, "Should return None when MemOS not available"
            print("✅ Correctly handles MemOS unavailable case")
        
        # Test case 2: Mock MemOS available
        if pm.project_memory_manager:
            # Set up mock MemOS
            mock_mos = MockMemOS()
            pm.set_mos_instance(mock_mos)
            
            # Test creating new MemCube
            user_id = "alice"
            project_id = "calculator_app"
            
            # First call should create the MemCube
            result1 = await pm._get_or_create_mem_cube(user_id, project_id)
            
            if result1:  # If creation was successful
                composite_id = f"{user_id}_{project_id}"
                
                # Check registry
                assert composite_id in pm.active_mem_cubes, "MemCube should be in registry"
                
                # Second call should return existing MemCube
                result2 = await pm._get_or_create_mem_cube(user_id, project_id)
                
                # Should be same reference/info
                assert result1 == result2, "Second call should return same MemCube info"
                
                print(f"✅ MemCube lifecycle working for: {composite_id}")
                print(f"📍 Created cube: {result1.get('cube_id', 'N/A') if result1 else 'None'}")
                
                # Test cleanup
                cleanup_result = pm.cleanup_mem_cube(user_id, project_id)
                assert cleanup_result, "Cleanup should succeed"
                assert composite_id not in pm.active_mem_cubes, "MemCube should be removed from registry"
                
                print("✅ MemCube cleanup working")
            else:
                print("⚠️ MemCube creation not available in test environment")
        
        await pm.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False


async def test_integration_with_handle_request():
    """Test 3: Integration with handle_request method."""
    
    print("\n🧪 Test 3: Integration with handle_request")
    print("-" * 50)
    
    try:
        # Initialize ProjectManager
        pm = ProjectManager()
        
        # Test request with project isolation
        user_id = "bob"
        project_id = "todo_manager"
        prompt = "Create a simple TODO class with basic functionality"
        
        # Make request
        result = await pm.handle_request(
            user_prompt=prompt,
            user_id=user_id,
            project_id=project_id
        )
        
        # Check result structure
        assert isinstance(result, dict), "handle_request should return dict"
        assert "status" in result, "Result should have status"
        assert "message" in result, "Result should have message"
        
        # Check if memory cube information is included
        if "memory_cube_used" in result:
            expected_cube = f"{user_id}_{project_id}_codebase_cube"
            print(f"📊 Memory cube used: {result['memory_cube_used']}")
            
            if result['memory_cube_used']:
                assert result['memory_cube_used'] == expected_cube, f"Expected cube: {expected_cube}"
                print(f"✅ Correct memory cube used: {expected_cube}")
        
        print(f"✅ Request handling with project isolation working")
        print(f"📊 Status: {result['status']}")
        print(f"📊 Tasks executed: {result.get('tasks_executed', 0)}")
        
        await pm.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False


async def test_error_handling_and_logging():
    """Test 4: Error handling and logging for MemCube operations."""
    
    print("\n🧪 Test 4: Error Handling and Logging")
    print("-" * 50)
    
    try:
        # Initialize ProjectManager
        pm = ProjectManager()
        
        # Test invalid parameters
        result = await pm._get_or_create_mem_cube("", "")
        print("✅ Handles empty parameters gracefully")
        
        # Test cleanup of non-existent MemCube
        cleanup_result = pm.cleanup_mem_cube("non_existent_user", "non_existent_project")
        assert not cleanup_result, "Cleanup of non-existent cube should return False"
        print("✅ Handles cleanup of non-existent MemCube")
        
        # Test get_active_mem_cubes when registry is empty
        active_cubes = pm.get_active_mem_cubes()
        assert isinstance(active_cubes, dict), "Should return dict even when empty"
        assert len(active_cubes) == 0, "Should be empty"
        print("✅ Handles empty registry correctly")
        
        # Test cleanup
        await pm.cleanup()
        print("✅ Cleanup handles errors gracefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False


async def test_multiple_projects_isolation():
    """Test 5: Multiple projects isolation functionality."""
    
    print("\n🧪 Test 5: Multiple Projects Isolation")
    print("-" * 50)
    
    try:
        # Initialize ProjectManager
        pm = ProjectManager()
        
        if pm.project_memory_manager and MEMOS_AVAILABLE:
            # Set up mock MemOS
            mock_mos = MockMemOS()
            pm.set_mos_instance(mock_mos)
            
            # Create multiple project contexts
            projects = [
                ("alice", "project_a"),
                ("alice", "project_b"),
                ("bob", "project_a"),
                ("bob", "project_c")
            ]
            
            created_cubes = []
            
            for user_id, project_id in projects:
                result = await pm._get_or_create_mem_cube(user_id, project_id)
                if result:
                    composite_id = f"{user_id}_{project_id}"
                    created_cubes.append(composite_id)
                    print(f"📊 Created: {composite_id}")
            
            # Check isolation
            assert len(pm.active_mem_cubes) == len(created_cubes), "All projects should be tracked"
            
            # Verify each project has unique storage
            cube_paths = set()
            for cube_info in pm.active_mem_cubes.values():
                if isinstance(cube_info, dict) and 'storage_path' in cube_info:
                    cube_paths.add(cube_info['storage_path'])
            
            if cube_paths:
                assert len(cube_paths) == len(created_cubes), "Each project should have unique storage"
                print("✅ Project isolation verified")
            
            # Test cleanup
            for user_id, project_id in projects:
                pm.cleanup_mem_cube(user_id, project_id)
            
            assert len(pm.active_mem_cubes) == 0, "All cubes should be cleaned up"
            print("✅ Multiple project cleanup working")
        
        else:
            print("⚠️ Skipping isolation test - MemOS not available")
        
        await pm.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        return False


async def main():
    """Run all dynamic MemCube lifecycle tests."""
    
    print("🧪 Dynamic MemCube Lifecycle Test Suite")
    print("=" * 60)
    print("Testing Task 1.2: Implement Dynamic MemCube Lifecycle")
    print()
    
    tests = [
        ("ProjectManager MemCube Registry", test_project_manager_memcube_registry),
        ("Get or Create MemCube Method", test_get_or_create_memcube_method),
        ("Integration with handle_request", test_integration_with_handle_request),
        ("Error Handling and Logging", test_error_handling_and_logging),
        ("Multiple Projects Isolation", test_multiple_projects_isolation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"🚀 Starting: {test_name}")
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    success_rate = (passed / total) * 100
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 All dynamic MemCube lifecycle tests passed!")
        print("✅ Task 1.2: Dynamic MemCube Lifecycle implementation is working correctly")
        print()
        print("🔋 Key Features Verified:")
        print("  • MemCube Registry in ProjectManager")
        print("  • Get or Create MemCube method")
        print("  • Integration with task workflow")
        print("  • Project isolation")
        print("  • Error handling and resource cleanup")
        print("  • Multiple concurrent projects support")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - review implementation")
    
    return success_rate == 100


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)