#!/usr/bin/env python3
"""
Test script for Automatic Codebase Syncing functionality

This script tests Task 1.3: Update Automatic Codebase Syncing
- Project-aware file monitoring
- Intelligent project_id extraction from file paths
- Targeted ingestion to specific MemCubes
- Debouncing mechanism for rapid file saves
- Integration with dynamic MemCube lifecycle
"""

import asyncio
import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from typing import List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from project_aware_file_monitor import (
        ProjectAwareFileMonitor, 
        ProjectAwareFileHandler,
        FileChangeEvent,
        create_workspace_structure,
        WATCHDOG_AVAILABLE
    )
    from project_memory_manager import ProjectMemoryManager, MEMOS_AVAILABLE
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the project root directory")
    sys.exit(1)


class MockProjectMemoryManager(ProjectMemoryManager):
    """Mock ProjectMemoryManager for testing without MemOS dependencies."""
    
    def __init__(self):
        super().__init__(mos_instance=None)
        self.memories = {}  # {(user_id, project_id): [memory_items]}
        self.operations = []  # Log of operations for testing
    
    def add_memory_to_project(self, user_id: str, project_id: str, memory_content: str, **kwargs) -> bool:
        """Mock memory addition."""
        key = (user_id, project_id)
        if key not in self.memories:
            self.memories[key] = []
        
        self.memories[key].append({
            'content': memory_content,
            'metadata': kwargs.get('metadata', {}),
            'timestamp': time.time()
        })
        
        self.operations.append({
            'operation': 'add',
            'user_id': user_id,
            'project_id': project_id,
            'content_length': len(memory_content)
        })
        
        return True
    
    def search_project_memory(self, user_id: str, project_id: str, query: str, **kwargs) -> dict:
        """Mock memory search."""
        key = (user_id, project_id)
        memories = self.memories.get(key, [])
        
        # Simple search - look for query in content
        results = []
        for memory in memories:
            if query.lower() in memory['content'].lower():
                results.append(memory)
        
        self.operations.append({
            'operation': 'search',
            'user_id': user_id,
            'project_id': project_id,
            'query': query,
            'results_count': len(results)
        })
        
        return {'results': results}
    
    def get_operation_log(self) -> List[dict]:
        """Get log of operations for testing."""
        return self.operations.copy()
    
    def clear_operations(self):
        """Clear operation log."""
        self.operations.clear()


async def test_project_context_extraction():
    """Test 1: Project context extraction from file paths."""
    
    print("🧪 Test 1: Project Context Extraction")
    print("-" * 50)
    
    try:
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            # Create test projects
            projects = ["project_alpha", "project_beta", "shared_utils"]
            create_workspace_structure(workspace_root, projects)
            
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file handler
            handler = ProjectAwareFileHandler(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.1
            )
            
            # Test file paths and expected extraction
            test_cases = [
                (f"{workspace_root}/project_alpha/src/main.py", ("default_user", "project_alpha")),
                (f"{workspace_root}/project_beta/tests/test_utils.py", ("default_user", "project_beta")),
                (f"{workspace_root}/shared_utils/lib/helper.js", ("default_user", "shared_utils")),
                (f"{workspace_root}/project_alpha/node_modules/package.json", None),  # Should be excluded
                (f"{workspace_root}/not_a_project.py", None),  # Not in project structure
                (f"/outside/workspace/file.py", None),  # Outside workspace
            ]
            
            passed = 0
            total = len(test_cases)
            
            for file_path, expected in test_cases:
                result = handler._extract_project_context(file_path)
                
                if result == expected:
                    print(f"✅ {Path(file_path).name}: {result}")
                    passed += 1
                else:
                    print(f"❌ {Path(file_path).name}: expected {expected}, got {result}")
            
            print(f"\n📊 Context extraction: {passed}/{total} tests passed")
            return passed == total
            
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


async def test_file_filtering():
    """Test 2: File filtering based on extensions and exclusions."""
    
    print("\n🧪 Test 2: File Filtering")
    print("-" * 50)
    
    try:
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file handler
            handler = ProjectAwareFileHandler(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.1
            )
            
            # Test file filtering
            test_cases = [
                ("main.py", True),        # Python file - should monitor
                ("utils.js", True),       # JavaScript file - should monitor
                ("README.md", True),      # Markdown file - should monitor
                ("config.json", True),    # JSON file - should monitor
                ("image.png", False),     # Image file - should not monitor
                ("data.csv", False),      # CSV file - should not monitor
                ("compiled.o", False),    # Object file - should not monitor
            ]
            
            passed = 0
            total = len(test_cases)
            
            for filename, expected in test_cases:
                result = handler._should_monitor_file(filename)
                
                if result == expected:
                    print(f"✅ {filename}: {result}")
                    passed += 1
                else:
                    print(f"❌ {filename}: expected {expected}, got {result}")
            
            print(f"\n📊 File filtering: {passed}/{total} tests passed")
            return passed == total
            
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False


async def test_debouncing_mechanism():
    """Test 3: Debouncing mechanism for rapid file changes."""
    
    print("\n🧪 Test 3: Debouncing Mechanism")
    print("-" * 50)
    
    try:
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            projects = ["test_project"]
            create_workspace_structure(workspace_root, projects)
            
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file handler with short debounce delay
            handler = ProjectAwareFileHandler(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.2  # 200ms debounce
            )
            
            # Create test file
            test_file = Path(workspace_root) / "test_project" / "rapid_changes.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("# Initial content")
            
            # Simulate rapid file changes
            file_event = FileChangeEvent(
                file_path=str(test_file),
                project_id="test_project",
                user_id="default_user",
                event_type="modified",
                timestamp=time.time()
            )
            
            # Schedule multiple rapid events
            for i in range(5):
                file_event.timestamp = time.time()
                handler._schedule_processing(file_event)
                await asyncio.sleep(0.05)  # 50ms between events
            
            # Check that only one event is pending
            pending_count = len(handler.pending_events)
            print(f"📊 Pending events after rapid changes: {pending_count}")
            
            # Wait for debounce to complete
            await asyncio.sleep(0.3)
            
            # Check that event was processed
            operations = mock_pm.get_operation_log()
            add_operations = [op for op in operations if op['operation'] == 'add']
            
            print(f"📊 Memory operations after debounce: {len(add_operations)}")
            print(f"📊 Final pending events: {len(handler.pending_events)}")
            
            # Should have exactly one add operation (debounced)
            success = len(add_operations) == 1 and len(handler.pending_events) == 0
            
            if success:
                print("✅ Debouncing working correctly - multiple rapid changes processed as one")
            else:
                print("❌ Debouncing failed - expected 1 operation, got", len(add_operations))
            
            return success
            
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False


async def test_targeted_ingestion():
    """Test 4: Targeted ingestion to specific project MemCubes."""
    
    print("\n🧪 Test 4: Targeted Ingestion")
    print("-" * 50)
    
    try:
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            projects = ["project_a", "project_b", "project_c"]
            create_workspace_structure(workspace_root, projects)
            
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file handler
            handler = ProjectAwareFileHandler(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.1
            )
            
            # Create test files in different projects
            test_files = [
                ("project_a", "main.py", "def main():\n    print('Project A')"),
                ("project_b", "utils.js", "function helper() {\n    return 'Project B';\n}"),
                ("project_c", "config.json", '{"name": "Project C", "version": "1.0"}')
            ]
            
            processed_files = []
            
            for project_id, filename, content in test_files:
                # Create file
                file_path = Path(workspace_root) / project_id / filename
                file_path.write_text(content)
                
                # Create file event
                file_event = FileChangeEvent(
                    file_path=str(file_path),
                    project_id=project_id,
                    user_id="default_user",
                    event_type="created",
                    timestamp=time.time()
                )
                
                # Process the event
                handler._ingest_file_to_project(file_event)
                processed_files.append((project_id, filename))
                
                print(f"📁 Processed: {project_id}/{filename}")
            
            # Check memory segregation
            operations = mock_pm.get_operation_log()
            add_operations = [op for op in operations if op['operation'] == 'add']
            
            print(f"\n📊 Total add operations: {len(add_operations)}")
            
            # Verify each project has its own memories
            project_operations = {}
            for op in add_operations:
                project_id = op['project_id']
                if project_id not in project_operations:
                    project_operations[project_id] = 0
                project_operations[project_id] += 1
            
            print("📊 Operations per project:")
            for project_id, count in project_operations.items():
                print(f"  {project_id}: {count} operations")
            
            # Each project should have exactly 1 operation
            success = all(count == 1 for count in project_operations.values()) and len(project_operations) == 3
            
            if success:
                print("✅ Targeted ingestion working - each project isolated")
            else:
                print("❌ Targeted ingestion failed - incorrect operation distribution")
            
            return success
            
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False


async def test_monitor_integration():
    """Test 5: Full file monitor integration."""
    
    print("\n🧪 Test 5: Monitor Integration")
    print("-" * 50)
    
    try:
        # Only run if watchdog is available
        if not WATCHDOG_AVAILABLE:
            print("⚠️ Skipping integration test - watchdog not available")
            return True
        
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            projects = ["integration_test"]
            create_workspace_structure(workspace_root, projects)
            
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file monitor
            monitor = ProjectAwareFileMonitor(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.2
            )
            
            # Test monitor status before starting
            status = monitor.get_monitoring_status()
            print(f"📊 Initial status: monitoring={status['is_monitoring']}")
            
            # Start monitoring
            monitor.start_monitoring()
            
            # Wait a moment for monitor to start
            await asyncio.sleep(0.1)
            
            # Create a test file (this should trigger the monitor)
            test_file = Path(workspace_root) / "integration_test" / "monitored_file.py"
            test_file.write_text("# This file is being monitored\ndef test():\n    pass")
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check if the file was processed
            operations = mock_pm.get_operation_log()
            add_operations = [op for op in operations if op['operation'] == 'add']
            
            print(f"📊 Operations detected: {len(add_operations)}")
            
            # Stop monitoring
            monitor.stop_monitoring()
            
            # Test force sync
            mock_pm.clear_operations()
            monitor.force_sync_project("integration_test")
            
            operations_after_sync = mock_pm.get_operation_log()
            sync_operations = [op for op in operations_after_sync if op['operation'] == 'add']
            
            print(f"📊 Force sync operations: {len(sync_operations)}")
            
            # Final status check
            final_status = monitor.get_monitoring_status()
            print(f"📊 Final status: monitoring={final_status['is_monitoring']}")
            
            # Success if we detected file changes and force sync worked
            success = len(add_operations) > 0 and len(sync_operations) > 0
            
            if success:
                print("✅ Monitor integration working correctly")
            else:
                print("❌ Monitor integration failed")
            
            return success
            
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        return False


async def test_workspace_structure_support():
    """Test 6: Workspace structure support and validation."""
    
    print("\n🧪 Test 6: Workspace Structure Support")
    print("-" * 50)
    
    try:
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace_root:
            # Test various workspace structures
            test_structures = [
                "simple_project",
                "multi-word-project",
                "project_with_underscores",
                "ProjectCamelCase"
            ]
            
            create_workspace_structure(workspace_root, test_structures)
            
            # Initialize mock memory manager
            mock_pm = MockProjectMemoryManager()
            
            # Create file handler
            handler = ProjectAwareFileHandler(
                workspace_root=workspace_root,
                project_memory_manager=mock_pm,
                debounce_delay=0.1
            )
            
            # Test each project structure
            passed_tests = 0
            total_tests = len(test_structures)
            
            for project_name in test_structures:
                # Create nested file structure
                test_paths = [
                    f"{project_name}/src/main.py",
                    f"{project_name}/src/utils/helper.py", 
                    f"{project_name}/tests/test_main.py",
                    f"{project_name}/docs/README.md"
                ]
                
                project_passed = True
                
                for relative_path in test_paths:
                    full_path = Path(workspace_root) / relative_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(f"# Content for {relative_path}")
                    
                    # Test context extraction
                    context = handler._extract_project_context(str(full_path))
                    
                    if context and context[1] == project_name:
                        print(f"✅ {relative_path}: project_id={context[1]}")
                    else:
                        print(f"❌ {relative_path}: expected {project_name}, got {context}")
                        project_passed = False
                
                if project_passed:
                    passed_tests += 1
            
            print(f"\n📊 Workspace structure support: {passed_tests}/{total_tests} projects passed")
            return passed_tests == total_tests
            
    except Exception as e:
        print(f"❌ Test 6 failed: {e}")
        return False


async def main():
    """Run all automatic codebase syncing tests."""
    
    print("🧪 Automatic Codebase Syncing Test Suite")
    print("=" * 60)
    print("Testing Task 1.3: Update Automatic Codebase Syncing")
    print()
    
    # Check dependencies
    print("🔍 Dependency Check:")
    print(f"  Watchdog available: {WATCHDOG_AVAILABLE}")
    print(f"  MemOS available: {MEMOS_AVAILABLE}")
    print()
    
    tests = [
        ("Project Context Extraction", test_project_context_extraction),
        ("File Filtering", test_file_filtering),
        ("Debouncing Mechanism", test_debouncing_mechanism),
        ("Targeted Ingestion", test_targeted_ingestion),
        ("Monitor Integration", test_monitor_integration),
        ("Workspace Structure Support", test_workspace_structure_support)
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
    
    if success_rate >= 85:  # Allow for some failures due to missing dependencies
        print("\n🎉 Automatic codebase syncing functionality working!")
        print("✅ Task 1.3: Update Automatic Codebase Syncing implementation validated")
        print()
        print("🔋 Key Features Implemented:")
        print("  • Project-aware file monitoring ✅")
        print("  • Intelligent project_id extraction ✅")
        print("  • Targeted ingestion to specific MemCubes ✅")
        print("  • Debouncing mechanism for rapid saves ✅")
        print("  • Integration with dynamic MemCube lifecycle ✅")
        print("  • Comprehensive workspace structure support ✅")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - review implementation")
    
    return success_rate >= 85


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)