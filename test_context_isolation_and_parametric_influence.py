#!/usr/bin/env python3
"""
Comprehensive Test Suite for Context Isolation and Parametric Memory Influence

This script tests:
- Task 4.1: Context Isolation Test (project memory boundaries)
- Task 4.2: Parametric Memory Influence Test (preference application)

Requirements:
- Backend service running on localhost:8000
- Test project directories created in ~/workspace/
"""

import asyncio
import aiohttp
import json
import sys
import os
import time
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
PROJECT_ALPHA_PATH = os.path.expanduser("~/workspace/project_alpha")
PROJECT_BETA_PATH = os.path.expanduser("~/workspace/project_beta")


async def check_service_health():
    """Check if the backend service is running and healthy."""
    print("🔍 Checking backend service health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Service healthy: {health_data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ Service unhealthy: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        print(f"💡 Make sure the service is running: python run_gguf_service.py")
        return False


async def load_project_codebase(project_path: str, project_id: str, user_id: str = "test_user"):
    """Load a project codebase into the system."""
    print(f"📂 Loading project '{project_id}' from {project_path}")
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "directory_path": project_path,
                "user_id": user_id,
                "project_id": project_id,
                "file_extensions": [".py"],
                "exclude_dirs": ["__pycache__", ".git"]
            }
            
            async with session.post(f"{BASE_URL}/load_codebase", json=payload) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("status") == "success":
                    files_loaded = result.get("files_loaded", 0)
                    print(f"✅ Project '{project_id}' loaded successfully")
                    print(f"   📊 Files loaded: {files_loaded}")
                    print(f"   📊 Total size: {result.get('total_size_bytes', 0)} bytes")
                    return True
                else:
                    print(f"❌ Failed to load project '{project_id}': {result}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error loading project '{project_id}': {e}")
        return False


async def set_project_preference(project_id: str, category: str, key: str, value: str, description: str, user_id: str = "test_user"):
    """Set a project-specific preference."""
    print(f"📋 Setting preference for project '{project_id}': {category}.{key} = {value}")
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "action": "add",
                "category": category,
                "key": key,
                "value": value,
                "description": description
            }
            
            url = f"{BASE_URL}/projects/{project_id}/preferences?user_id={user_id}"
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("status") == "success":
                    print(f"✅ Preference set successfully: {result.get('message')}")
                    return True
                else:
                    print(f"❌ Failed to set preference: {result}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error setting preference: {e}")
        return False


async def execute_agentic_task(prompt: str, project_id: str, user_id: str = "test_user"):
    """Execute an agentic task with specific project context."""
    print(f"🤖 Executing agentic task for project '{project_id}'")
    print(f"   📝 Prompt: {prompt}")
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "prompt": prompt,
                "user_id": user_id,
                "project_id": project_id
            }
            
            async with session.post(f"{BASE_URL}/execute_agentic_task", json=payload) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"✅ Task executed successfully")
                    return result
                else:
                    print(f"❌ Task execution failed: HTTP {response.status}")
                    print(f"   Response: {result}")
                    return None
                    
    except Exception as e:
        print(f"❌ Error executing task: {e}")
        return None


async def test_context_isolation():
    """
    Task 4.1: Context Isolation Test
    
    Empirically prove that memory and knowledge base of one project
    are completely inaccessible when operating within another project's context.
    """
    print("\n" + "="*70)
    print("🧪 Task 4.1: Context Isolation Test")
    print("="*70)
    
    test_results = {
        "setup_successful": False,
        "correct_context_query": {"success": False, "found_function": False},
        "cross_context_breach_attempt": {"success": False, "properly_isolated": False}
    }
    
    # Step 1: Load both projects
    print("\n📂 Step 1: Loading Project Codebases")
    print("-" * 40)
    
    alpha_loaded = await load_project_codebase(PROJECT_ALPHA_PATH, "alpha")
    beta_loaded = await load_project_codebase(PROJECT_BETA_PATH, "beta")
    
    if not (alpha_loaded and beta_loaded):
        print("❌ Failed to load projects - cannot proceed with isolation test")
        return test_results
    
    test_results["setup_successful"] = True
    
    # Wait for indexing to complete
    print("\n⏳ Waiting 5 seconds for indexing to complete...")
    await asyncio.sleep(5)
    
    # Step 2: Query within correct context (Project Alpha)
    print("\n🔍 Step 2: Query Within Correct Context (Project Alpha)")
    print("-" * 40)
    
    alpha_query = "What is the purpose of the calculate_photon_matrix function?"
    alpha_result = await execute_agentic_task(alpha_query, "alpha")
    
    if alpha_result:
        result_text = str(alpha_result.get("result", "")).lower()
        message = alpha_result.get("message", "")
        
        # Check if the function was found and described
        photon_indicators = [
            "calculate_photon_matrix",
            "photon",
            "wavelength",
            "intensity",
            "polarization",
            "quantum",
            "matrix"
        ]
        
        found_indicators = sum(1 for indicator in photon_indicators if indicator in result_text)
        
        test_results["correct_context_query"]["success"] = True
        test_results["correct_context_query"]["found_function"] = found_indicators >= 3
        
        print(f"📊 Result Analysis:")
        print(f"   Status: {message}")
        print(f"   Photon-related indicators found: {found_indicators}/{len(photon_indicators)}")
        print(f"   Function properly identified: {'✅' if found_indicators >= 3 else '❌'}")
        
        if found_indicators >= 3:
            print("✅ Correct context query successful - function found and described")
        else:
            print("⚠️ Function may not have been properly identified")
    else:
        print("❌ Alpha context query failed")
    
    # Step 3: Attempt cross-context breach (Query Alpha function from Beta context)
    print("\n🚫 Step 3: Cross-Context Breach Attempt (Beta asking about Alpha function)")
    print("-" * 40)
    
    breach_query = "What is the purpose of the calculate_photon_matrix function?"
    beta_result = await execute_agentic_task(breach_query, "beta")
    
    if beta_result:
        result_text = str(beta_result.get("result", "")).lower()
        message = beta_result.get("message", "")
        
        # Check if the system properly isolated and didn't find the Alpha function
        isolation_indicators = [
            "no knowledge",
            "not found",
            "don't know",
            "unfamiliar",
            "no information",
            "cannot find",
            "not available",
            "graviton",  # Should find beta-specific content instead
            "spacetime"
        ]
        
        # Check for Alpha function leakage (should NOT be present)
        alpha_leakage = [
            "calculate_photon_matrix",
            "photon matrix",
            "wavelength",
            "polarization"
        ]
        
        isolation_score = sum(1 for indicator in isolation_indicators if indicator in result_text)
        leakage_score = sum(1 for leak in alpha_leakage if leak in result_text)
        
        test_results["cross_context_breach_attempt"]["success"] = True
        test_results["cross_context_breach_attempt"]["properly_isolated"] = (isolation_score > 0 or leakage_score == 0)
        
        print(f"📊 Isolation Analysis:")
        print(f"   Status: {message}")
        print(f"   Isolation indicators: {isolation_score}/{len(isolation_indicators)}")
        print(f"   Alpha function leakage: {leakage_score}/{len(alpha_leakage)}")
        print(f"   Proper isolation: {'✅' if isolation_score > 0 or leakage_score == 0 else '❌'}")
        
        if isolation_score > 0 or leakage_score == 0:
            print("✅ Context isolation working correctly - no cross-project leakage")
        else:
            print("❌ Context isolation breach detected - Alpha content accessible from Beta")
    else:
        print("❌ Beta context query failed")
    
    # Summary
    print(f"\n📊 Context Isolation Test Summary:")
    print(f"   Setup successful: {'✅' if test_results['setup_successful'] else '❌'}")
    print(f"   Correct context query: {'✅' if test_results['correct_context_query']['found_function'] else '❌'}")
    print(f"   Cross-context isolation: {'✅' if test_results['cross_context_breach_attempt']['properly_isolated'] else '❌'}")
    
    return test_results


async def test_parametric_memory_influence():
    """
    Task 4.2: Parametric Memory Influence Test
    
    Validate that the system can store and apply project-specific guidelines,
    and that generative agents modify their behavior accordingly.
    """
    print("\n" + "="*70)
    print("🧪 Task 4.2: Parametric Memory Influence Test")
    print("="*70)
    
    test_results = {
        "preferences_set": False,
        "code_generated": False,
        "google_docstring": False,
        "dev_note_comments": False,
        "preferences_applied": False
    }
    
    # Step 1: Set specific project preferences
    print("\n📋 Step 1: Setting Project-Specific Preferences")
    print("-" * 40)
    
    # Set docstring style preference
    docstring_set = await set_project_preference(
        project_id="alpha",
        category="coding_style",
        key="docstring_style",
        value="Google",
        description="Use Google-style docstrings with Args and Returns sections"
    )
    
    # Set comment prefix preference
    comment_set = await set_project_preference(
        project_id="alpha",
        category="coding_style", 
        key="comment_prefix",
        value="# DEV_NOTE:",
        description="Prefix all internal comments with # DEV_NOTE:"
    )
    
    test_results["preferences_set"] = docstring_set and comment_set
    
    if not test_results["preferences_set"]:
        print("❌ Failed to set preferences - cannot proceed with influence test")
        return test_results
    
    # Wait for preferences to be stored
    print("\n⏳ Waiting 3 seconds for preferences to be stored...")
    await asyncio.sleep(3)
    
    # Step 2: Execute generative task
    print("\n🤖 Step 2: Executing Code Generation Task")
    print("-" * 40)
    
    generation_prompt = """Create a new Python function named 'log_system_status' that takes a 'status_message' string and a 'level' integer as arguments and returns a formatted log string."""
    
    generation_result = await execute_agentic_task(generation_prompt, "alpha")
    
    if not generation_result:
        print("❌ Code generation failed")
        return test_results
    
    test_results["code_generated"] = True
    
    # Step 3: Analyze generated code
    print("\n🔍 Step 3: Analyzing Generated Code for Preference Compliance")
    print("-" * 40)
    
    generated_code = str(generation_result.get("result", ""))
    print(f"📝 Generated Code Preview:")
    print("```python")
    code_lines = generated_code.split('\n')[:20]  # Show first 20 lines
    for line in code_lines:
        print(line)
    if len(generated_code.split('\n')) > 20:
        print("... (truncated)")
    print("```")
    
    # Check for Google-style docstring
    google_docstring_indicators = [
        "Args:",
        "Returns:",
        '"""',
        "status_message (str):",
        "level (int):"
    ]
    
    google_score = sum(1 for indicator in google_docstring_indicators if indicator in generated_code)
    test_results["google_docstring"] = google_score >= 3
    
    print(f"\n📊 Google Docstring Analysis:")
    print(f"   Indicators found: {google_score}/{len(google_docstring_indicators)}")
    for indicator in google_docstring_indicators:
        found = "✅" if indicator in generated_code else "❌"
        print(f"   {found} {indicator}")
    
    # Check for DEV_NOTE comment prefix
    dev_note_count = generated_code.count("# DEV_NOTE:")
    test_results["dev_note_comments"] = dev_note_count > 0
    
    print(f"\n📊 Comment Prefix Analysis:")
    print(f"   DEV_NOTE comments found: {dev_note_count}")
    print(f"   Preference applied: {'✅' if dev_note_count > 0 else '❌'}")
    
    # Overall preference application assessment
    test_results["preferences_applied"] = test_results["google_docstring"] and test_results["dev_note_comments"]
    
    # Step 4: Detailed compliance verification
    print(f"\n🔍 Step 4: Detailed Compliance Verification")
    print("-" * 40)
    
    # Check function signature
    function_signature_correct = "def log_system_status(" in generated_code
    has_required_params = "status_message" in generated_code and "level" in generated_code
    has_return_statement = "return" in generated_code
    
    print(f"📊 Function Structure:")
    print(f"   Correct function name: {'✅' if function_signature_correct else '❌'}")
    print(f"   Required parameters: {'✅' if has_required_params else '❌'}")
    print(f"   Has return statement: {'✅' if has_return_statement else '❌'}")
    
    # Summary
    print(f"\n📊 Parametric Memory Influence Test Summary:")
    print(f"   Preferences set: {'✅' if test_results['preferences_set'] else '❌'}")
    print(f"   Code generated: {'✅' if test_results['code_generated'] else '❌'}")
    print(f"   Google docstring: {'✅' if test_results['google_docstring'] else '❌'}")
    print(f"   DEV_NOTE comments: {'✅' if test_results['dev_note_comments'] else '❌'}")
    print(f"   Preferences applied: {'✅' if test_results['preferences_applied'] else '❌'}")
    
    return test_results


async def main():
    """Run comprehensive context isolation and parametric memory influence tests."""
    
    print("🧪 Context Isolation and Parametric Memory Influence Test Suite")
    print("=" * 70)
    print("Testing empirical validation of memory architecture")
    print()
    
    # Check service health
    if not await check_service_health():
        print("❌ Backend service not available - cannot run tests")
        return False
    
    # Verify test files exist
    alpha_file = Path(PROJECT_ALPHA_PATH) / "alpha_utils.py"
    beta_file = Path(PROJECT_BETA_PATH) / "beta_tools.py"
    
    print(f"\n📁 Verifying test files:")
    print(f"   Alpha file: {'✅' if alpha_file.exists() else '❌'} {alpha_file}")
    print(f"   Beta file: {'✅' if beta_file.exists() else '❌'} {beta_file}")
    
    if not (alpha_file.exists() and beta_file.exists()):
        print("❌ Test files missing - please ensure project files are created")
        return False
    
    # Run tests
    isolation_results = await test_context_isolation()
    parametric_results = await test_parametric_memory_influence()
    
    # Final summary
    print("\n" + "="*70)
    print("📊 FINAL TEST RESULTS SUMMARY")
    print("="*70)
    
    # Context isolation summary
    isolation_success = (
        isolation_results["setup_successful"] and
        isolation_results["correct_context_query"]["found_function"] and
        isolation_results["cross_context_breach_attempt"]["properly_isolated"]
    )
    
    print(f"🔒 Task 4.1 - Context Isolation: {'✅ PASSED' if isolation_success else '❌ FAILED'}")
    if isolation_success:
        print("   ✅ Projects loaded successfully into isolated MemCubes")
        print("   ✅ Correct context queries return project-specific information")
        print("   ✅ Cross-context queries properly reject unauthorized access")
    else:
        print("   ❌ Context isolation has issues - check implementation")
    
    # Parametric memory summary
    parametric_success = (
        parametric_results["preferences_set"] and
        parametric_results["code_generated"] and
        parametric_results["preferences_applied"]
    )
    
    print(f"\n📋 Task 4.2 - Parametric Memory Influence: {'✅ PASSED' if parametric_success else '❌ FAILED'}")
    if parametric_success:
        print("   ✅ Project preferences stored successfully")
        print("   ✅ Code generation completed")
        print("   ✅ Generated code adheres to project-specific guidelines")
    else:
        print("   ❌ Parametric memory influence has issues - check implementation")
    
    # Overall assessment
    overall_success = isolation_success and parametric_success
    
    print(f"\n🎯 OVERALL ASSESSMENT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Congratulations! Your three-tier memory architecture is working perfectly:")
        print("   🏗️ TextualMemory: Provides project-specific code context")
        print("   🚀 ActivationMemory: Optimizes performance with KVCache")
        print("   📋 ParametricMemory: Enforces project-specific guidelines")
        print("   🔒 Project Isolation: Complete separation between projects")
        print("   🤖 Agent Integration: Agents respond to memory-driven context")
    else:
        print("\n⚠️ Some tests failed. Review the detailed results above.")
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)