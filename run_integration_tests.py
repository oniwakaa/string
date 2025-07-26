#!/usr/bin/env python3
"""
Integration Test Runner for AI Coding Assistant

This script provides a convenient way to run the full stack integration tests
with proper environment setup and comprehensive reporting.

Usage:
    python run_integration_tests.py [options]
    
Options:
    --server-check: Verify backend service is running before tests
    --cleanup: Clean up test artifacts after completion
    --report-only: Generate report from previous test run
    --workspace-dir: Custom test workspace directory
    
Requirements:
    - Backend service running on http://127.0.0.1:8000
    - All models downloaded and configured
    - Write permissions in current directory
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_server_health(server_url: str = "http://127.0.0.1:8000") -> bool:
    """Check if the backend service is running and healthy"""
    
    try:
        limits = httpx.Limits(max_connections=5, max_keepalive_connections=3)
        async with httpx.AsyncClient(timeout=5.0, limits=limits) as client:
            response = await client.get(f"{server_url}/health")
            if response.status_code == 200:
                logger.info("✅ Backend service is healthy")
                return True
            else:
                logger.error(f"❌ Backend service returned status {response.status_code}")
                return False
                
    except httpx.RequestError as e:
        logger.error(f"❌ Cannot connect to backend service: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error checking service: {e}")
        return False

def run_pytest_with_options(test_file: str, workspace_dir: str = None) -> int:
    """Run pytest with appropriate options"""
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v", "-s",
        "--tb=short",
        "-m", "not slow"  # Skip slow tests by default
    ]
    
    env = os.environ.copy()
    if workspace_dir:
        env["WORKSPACE_ROOT"] = workspace_dir
    
    logger.info(f"🚀 Running integration tests: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env=env, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        logger.info("🛑 Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Error running tests: {e}")
        return 1

def cleanup_test_artifacts():
    """Clean up test artifacts and temporary files"""
    
    cleanup_patterns = [
        "test_workspace",
        "tests/integration/full_stack_test.log",
        "generated_api.py",
        "broken_module.py",
        "**/__pycache__",
        "**/*.pyc"
    ]
    
    logger.info("🧹 Cleaning up test artifacts...")
    
    for pattern in cleanup_patterns:
        for path in Path(".").glob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    logger.debug(f"Removed file: {path}")
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    logger.debug(f"Removed directory: {path}")
            except Exception as e:
                logger.warning(f"Could not remove {path}: {e}")

def generate_report_summary():
    """Generate and display test report summary"""
    
    report_file = Path("tests/integration/test_report.json")
    
    if not report_file.exists():
        logger.warning("📋 No test report found. Run tests first.")
        return
    
    try:
        with open(report_file) as f:
            report = json.load(f)
        
        print("\n" + "="*60)
        print("📊 INTEGRATION TEST REPORT SUMMARY")
        print("="*60)
        
        # Test session info
        session = report.get('test_session', {})
        print(f"📅 Timestamp: {session.get('timestamp', 'Unknown')}")
        print(f"📁 Workspace: {session.get('workspace', 'Unknown')}")
        print(f"🔢 Workflows: {session.get('total_workflows', 0)}")
        
        # Performance metrics
        perf = report.get('performance_summary', {})
        print(f"\n⏱️  Performance:")
        print(f"   Operations: {perf.get('total_operations', 0)}")
        print(f"   Total Time: {perf.get('total_time_seconds', 0):.2f}s")
        print(f"   Max Memory: {perf.get('max_memory_mb', 0):.1f}MB")
        print(f"   Avg CPU: {perf.get('average_cpu_percent', 0):.1f}%")
        
        # Coverage info
        coverage = report.get('coverage_summary', {})
        agents = coverage.get('agents_tested', [])
        features = coverage.get('features_validated', [])
        
        print(f"\n🎯 Coverage:")
        print(f"   Agents Tested: {len(agents)}")
        for agent in agents[:3]:  # Show first 3
            print(f"     • {agent}")
        if len(agents) > 3:
            print(f"     ... and {len(agents) - 3} more")
            
        print(f"   Features: {len(features)}")
        for feature in features[:3]:  # Show first 3
            print(f"     • {feature}")
        if len(features) > 3:
            print(f"     ... and {len(features) - 3} more")
        
        # Artifacts
        artifacts = report.get('test_artifacts', {})
        generated = artifacts.get('generated_files', [])
        if generated:
            print(f"\n📄 Generated Files: {len(generated)}")
            for file in generated[:3]:
                print(f"     • {file}")
            if len(generated) > 3:
                print(f"     ... and {len(generated) - 3} more")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error reading test report: {e}")

def main():
    """Main test runner function"""
    
    parser = argparse.ArgumentParser(
        description="Run full stack integration tests for AI coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--server-check", 
        action="store_true",
        help="Verify backend service is running before tests"
    )
    
    parser.add_argument(
        "--cleanup", 
        action="store_true",
        help="Clean up test artifacts after completion"
    )
    
    parser.add_argument(
        "--report-only", 
        action="store_true",
        help="Generate report from previous test run without running tests"
    )
    
    parser.add_argument(
        "--workspace-dir",
        type=str,
        help="Custom test workspace directory"
    )
    
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Backend service URL (default: http://127.0.0.1:8000)"
    )
    
    args = parser.parse_args()
    
    # Handle report-only mode
    if args.report_only:
        generate_report_summary()
        return 0
    
    # Check server health if requested
    if args.server_check:
        logger.info("🔍 Checking backend service health...")
        
        async def check():
            return await check_server_health(args.server_url)
        
        if not asyncio.run(check()):
            logger.error("❌ Backend service is not available. Please start it first:")
            logger.error("   python run_gguf_service.py")
            return 1
    
    # Run the integration tests
    test_file = "tests/integration/full_stack_pipeline_test.py"
    
    if not Path(test_file).exists():
        logger.error(f"❌ Test file not found: {test_file}")
        return 1
    
    exit_code = run_pytest_with_options(test_file, args.workspace_dir)
    
    # Generate report summary
    if exit_code == 0:
        logger.info("✅ All tests completed successfully")
        generate_report_summary()
    else:
        logger.error(f"❌ Tests failed with exit code: {exit_code}")
    
    # Cleanup if requested
    if args.cleanup:
        cleanup_test_artifacts()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())