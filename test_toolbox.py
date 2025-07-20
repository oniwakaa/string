"""
Test script for SecureToolbox functionality
"""

import sys
import os
sys.path.append('agents')

from toolbox import create_secure_toolbox

def test_toolbox():
    """Test all toolbox functionality."""
    print("🧪 Testing SecureToolbox Functionality")
    print("=" * 50)
    
    # Create toolbox instance
    toolbox = create_secure_toolbox()
    
    # Test 1: Security status
    print("\n📊 Test 1: Security Status")
    status = toolbox.get_security_status()
    print(f"✅ Project root: {status['project_root']}")
    print(f"✅ Allowed extensions: {len(status['allowed_extensions'])}")
    print(f"✅ Blocked paths: {len(status['blocked_paths'])}")
    print(f"✅ Max file size: {status['max_file_size']} bytes")
    
    # Test 2: File creation
    print("\n📝 Test 2: File Creation")
    result = toolbox.create_file(
        file_path="test_secure_file.py",
        content="""# Test file created by SecureToolbox
def hello_world():
    print("Hello from secure toolbox!")

if __name__ == "__main__":
    hello_world()
"""
    )
    
    if result['success']:
        print(f"✅ File created: {result['path']}")
        print(f"✅ Size: {result['size']} bytes")
        print(f"✅ Hash: {result['hash'][:16]}...")
    else:
        print(f"❌ File creation failed: {result['error']}")
    
    # Test 3: File editing
    print("\n📝 Test 3: File Editing")
    edit_result = toolbox.edit_file(
        file_path="test_secure_file.py",
        content="""# Test file edited by SecureToolbox
def hello_world():
    print("Hello from secure toolbox - EDITED!")

def new_function():
    return "This is a new function"

if __name__ == "__main__":
    hello_world()
    print(new_function())
"""
    )
    
    if edit_result['success']:
        print(f"✅ File edited: {edit_result['path']}")
        print(f"✅ New size: {edit_result['size']} bytes")
        print(f"✅ Backup created: {edit_result['backup_path'] is not None}")
    else:
        print(f"❌ File editing failed: {edit_result['error']}")
    
    # Test 4: Valid command execution
    print("\n💻 Test 4: Valid Command Execution")
    cmd_result = toolbox.run_terminal_command(['git', 'status', '--porcelain'])
    
    if cmd_result['success']:
        print(f"✅ Command executed: {cmd_result['command']}")
        print(f"✅ Exit code: {cmd_result['exit_code']}")
        print(f"✅ Execution time: {cmd_result['execution_time']:.3f}s")
    else:
        print(f"❌ Command failed: {cmd_result['error']}")
    
    # Test 5: Security validation (blocked command)
    print("\n🔒 Test 5: Security Validation (Blocked Command)")
    blocked_cmd = toolbox.run_terminal_command(['rm', '-rf', '*'])
    
    if not blocked_cmd['success']:
        print(f"✅ Blocked dangerous command: {blocked_cmd['error']}")
    else:
        print(f"❌ Security breach: dangerous command was allowed!")
    
    # Test 6: Path validation
    print("\n🔒 Test 6: Path Validation")
    try:
        dangerous_result = toolbox.create_file(
            file_path="../../../etc/passwd",
            content="hacker content"
        )
        if not dangerous_result['success']:
            print(f"✅ Blocked dangerous path: {dangerous_result['error']}")
        else:
            print(f"❌ Security breach: dangerous path was allowed!")
    except Exception as e:
        print(f"✅ Security validation caught exception: {str(e)}")
    
    # Test 7: Audit log
    print("\n📋 Test 7: Audit Log")
    log_entries = toolbox.get_audit_log(lines=5)
    print(f"✅ Retrieved {len(log_entries)} log entries")
    if log_entries:
        print("Recent log entry:")
        print(f"  {log_entries[-1].strip()}")
    
    print("\n🎉 All tests completed!")
    
    # Summary
    total_tests = 7
    passed_tests = 0
    
    # Count successful tests based on outputs
    if status['toolbox_initialized']:
        passed_tests += 1
    if result.get('success'):
        passed_tests += 1
    if edit_result.get('success'):
        passed_tests += 1
    if cmd_result.get('success'):
        passed_tests += 1
    if not blocked_cmd.get('success'):
        passed_tests += 1
    if 'Security' in str(dangerous_result.get('error', '')):
        passed_tests += 1
    if len(log_entries) > 0:
        passed_tests += 1
    
    print(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed")
    success_rate = (passed_tests / total_tests) * 100
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 85:
        print("🎉 SecureToolbox is working correctly!")
    else:
        print("⚠️ Some tests failed - review implementation")

if __name__ == "__main__":
    test_toolbox()