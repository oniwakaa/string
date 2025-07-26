#!/usr/bin/env python3
"""
Test Setup Validation Script

Validates that the integration test environment is properly configured
and all dependencies are available before running the full test suite.

Usage:
    python validate_test_setup.py
"""

import asyncio
import importlib
import sys
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("   ❌ Python 3.8+ required")
        return False
    
    print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_required_modules():
    """Check if required modules are available"""
    print("\n📦 Checking required modules...")
    
    required_modules = [
        'pytest',
        'httpx', 
        'psutil',
        'asyncio',
        'fastapi',
        'uvicorn'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} (missing)")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n   Install missing modules:")
        print(f"   pip install {' '.join(missing_modules)}")
        return False
    
    return True

def check_project_structure():
    """Check if project structure is correct"""
    print("\n📁 Checking project structure...")
    
    required_paths = [
        'src/',
        'agents/',
        'config/',
        'tests/',
        'tests/integration/',
        'run_gguf_service.py',
        'CLAUDE.md'
    ]
    
    missing_paths = []
    
    for path_str in required_paths:
        path = Path(path_str)
        if path.exists():
            print(f"   ✅ {path_str}")
        else:
            print(f"   ❌ {path_str} (missing)")
            missing_paths.append(path_str)
    
    if missing_paths:
        print(f"\n   Missing required project files/directories")
        return False
    
    return True

def check_test_files():
    """Check if test files are present"""
    print("\n🧪 Checking test files...")
    
    test_files = [
        'tests/integration/full_stack_pipeline_test.py',
        'tests/integration/README.md',
        'run_integration_tests.py',
        'pytest.ini'
    ]
    
    missing_files = []
    
    for file_str in test_files:
        file_path = Path(file_str)
        if file_path.exists():
            print(f"   ✅ {file_str}")
        else:
            print(f"   ❌ {file_str} (missing)")
            missing_files.append(file_str)
    
    return len(missing_files) == 0

async def check_server_connection():
    """Check if backend service is reachable"""
    print("\n🌐 Checking backend service...")
    
    try:
        import httpx
        
        limits = httpx.Limits(max_connections=5, max_keepalive_connections=3)
        async with httpx.AsyncClient(timeout=5.0, limits=limits) as client:
            response = await client.get("http://127.0.0.1:8000/health")
            
            if response.status_code == 200:
                print("   ✅ Backend service is running and healthy")
                return True
            else:
                print(f"   ⚠️  Backend service returned status {response.status_code}")
                return False
                
    except httpx.RequestError:
        print("   ⚠️  Backend service not running (start with: python run_gguf_service.py)")
        return False
    except Exception as e:
        print(f"   ❌ Error checking service: {e}")
        return False

def check_workspace_permissions():
    """Check workspace write permissions"""
    print("\n📝 Checking workspace permissions...")
    
    try:
        test_file = Path("test_write_permission.tmp")
        test_file.write_text("test")
        test_file.unlink()
        print("   ✅ Workspace is writable")
        return True
    except Exception as e:
        print(f"   ❌ Workspace not writable: {e}")
        return False

async def main():
    """Main validation function"""
    print("🔍 AI Coding Assistant - Integration Test Setup Validation")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Required Modules", check_required_modules()),
        ("Project Structure", check_project_structure()),
        ("Test Files", check_test_files()),
        ("Backend Service", await check_server_connection()),
        ("Workspace Permissions", check_workspace_permissions())
    ]
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = 0
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {check_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("\n🎉 All checks passed! Ready to run integration tests.")
        print("\nRun tests with:")
        print("   python run_integration_tests.py --server-check --cleanup")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix issues before running tests.")
        
        if not checks[4][1]:  # Backend service check
            print("\nTo start the backend service:")
            print("   python run_gguf_service.py")
        
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)