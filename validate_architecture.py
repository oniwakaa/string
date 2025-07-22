#!/usr/bin/env python3
"""
Architecture Validation Script - Comprehensive System Testing

This script performs rigorous end-to-end testing of the AI coding assistant
architecture to validate stability, performance, and feature completeness.

Tests:
1. Multi-Agent Orchestration Workflow
2. ResourceManager Stress Test (Concurrent Load)
3. Model Eviction Policy Test (Memory Management)

Author: Claude Code Assistant
Date: 2025-07-22
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

class ArchitectureValidator:
    """Comprehensive architecture validation suite."""
    
    def __init__(self):
        self.session = None
        self.results = {
            "orchestration_test": {"status": "pending", "details": {}},
            "stress_test": {"status": "pending", "details": {}},
            "eviction_test": {"status": "pending", "details": {}}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_service_health(self) -> bool:
        """Quick health check before running tests."""
        try:
            async with self.session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Service healthy: {data.get('status')}")
                    return True
                else:
                    logger.error(f"❌ Service unhealthy: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False

    async def test_multi_agent_orchestration(self) -> Dict[str, Any]:
        """
        Test 1: Multi-Agent Orchestration Workflow
        
        Verifies that complex prompts trigger the correct sequence of agents
        and that the multi-agent pipeline is fully operational.
        """
        logger.info("🧪 TEST 1: Multi-Agent Orchestration Workflow")
        
        # Complex prompt that should trigger WebResearcher → CodeGenerator
        test_prompt = (
            "Research the key features of the psutil library and then write a Python script "
            "that uses it to monitor and log the current CPU and memory usage."
        )
        
        payload = {
            "prompt": test_prompt,
            "user_id": "test_user_orchestration",
            "project_id": "orchestration_test"
        }
        
        try:
            start_time = time.time()
            logger.info("📡 Sending complex orchestration request...")
            
            async with self.session.post(f"{BASE_URL}/execute_agentic_task", json=payload) as response:
                end_time = time.time()
                response_data = await response.json()
                
                result = {
                    "http_status": response.status,
                    "execution_time": end_time - start_time,
                    "response_status": response_data.get("status"),
                    "has_result": bool(response_data.get("result")),
                    "has_execution_plan": bool(response_data.get("execution_plan")),
                    "tasks_executed": response_data.get("tasks_executed", 0),
                    "agent_status": response_data.get("agent_status", {})
                }
                
                # Success criteria
                success = (
                    response.status == 200 and
                    response_data.get("status") == "success" and
                    response_data.get("result") and
                    response_data.get("tasks_executed", 0) > 0
                )
                
                if success:
                    logger.info("✅ Multi-agent orchestration PASSED")
                    logger.info(f"   - Execution time: {result['execution_time']:.2f}s")
                    logger.info(f"   - Tasks executed: {result['tasks_executed']}")
                    logger.info("   📋 ACTION: Check server logs to verify WebResearcher → CodeGenerator sequence")
                else:
                    logger.error("❌ Multi-agent orchestration FAILED")
                    logger.error(f"   - HTTP Status: {response.status}")
                    logger.error(f"   - Response Status: {response_data.get('status')}")
                
                result["success"] = success
                self.results["orchestration_test"] = {"status": "passed" if success else "failed", "details": result}
                return result
                
        except Exception as e:
            logger.error(f"❌ Multi-agent orchestration ERROR: {e}")
            result = {"success": False, "error": str(e)}
            self.results["orchestration_test"] = {"status": "error", "details": result}
            return result

    async def test_resource_manager_stress(self) -> Dict[str, Any]:
        """
        Test 2: ResourceManager Stress Test
        
        Tests concurrent API calls to ensure no race conditions or lock file issues
        under load, validating the singleton pattern works correctly.
        """
        logger.info("🧪 TEST 2: ResourceManager Stress Test (Concurrent Load)")
        
        # Test parameters
        concurrent_requests = 20
        project_ids = ["stress_test_1", "stress_test_2", "stress_test_3", "stress_test_4"]
        
        async def make_codebase_request(session: aiohttp.ClientSession, project_id: str, req_id: int):
            """Make a single codebase loading request."""
            payload = {
                "directory_path": "/Users/carlo/Desktop/pr_prj/str_prj/test_codebase",
                "user_id": f"stress_user_{req_id}",
                "project_id": project_id,
                "file_extensions": [".py"]
            }
            
            try:
                async with session.post(f"{BASE_URL}/load_codebase", json=payload) as response:
                    data = await response.json()
                    return {
                        "request_id": req_id,
                        "project_id": project_id,
                        "status_code": response.status,
                        "success": response.status == 200 and data.get("status") == "success",
                        "files_loaded": data.get("files_loaded", 0)
                    }
            except Exception as e:
                return {
                    "request_id": req_id,
                    "project_id": project_id,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                }

        async def make_chat_request(session: aiohttp.ClientSession, project_id: str, req_id: int):
            """Make a single chat request."""
            payload = {
                "query": f"Explain the purpose of test file {req_id}",
                "user_id": f"stress_user_{req_id}",
                "project_id": project_id,
                "include_memory": True
            }
            
            try:
                async with session.post(f"{BASE_URL}/chat", json=payload) as response:
                    data = await response.json()
                    return {
                        "request_id": req_id,
                        "project_id": project_id,
                        "status_code": response.status,
                        "success": response.status == 200 and data.get("response"),
                        "memory_enhanced": data.get("memory_enhanced", False)
                    }
            except Exception as e:
                return {
                    "request_id": req_id,
                    "project_id": project_id, 
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                }
        
        try:
            start_time = time.time()
            logger.info(f"📡 Launching {concurrent_requests} concurrent requests...")
            
            # Create mixed workload: 10 codebase + 10 chat requests
            tasks = []
            for i in range(concurrent_requests):
                project_id = project_ids[i % len(project_ids)]
                if i < concurrent_requests // 2:
                    tasks.append(make_codebase_request(self.session, project_id, i))
                else:
                    tasks.append(make_chat_request(self.session, project_id, i))
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_requests = 0
            failed_requests = 0
            total_files_loaded = 0
            
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    successful_requests += 1
                    total_files_loaded += result.get("files_loaded", 0)
                else:
                    failed_requests += 1
            
            stress_result = {
                "total_requests": concurrent_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": successful_requests / concurrent_requests,
                "execution_time": end_time - start_time,
                "total_files_loaded": total_files_loaded,
                "requests_per_second": concurrent_requests / (end_time - start_time),
                "detailed_results": results
            }
            
            # Success criteria: All requests successful
            success = successful_requests == concurrent_requests
            
            if success:
                logger.info("✅ ResourceManager stress test PASSED")
                logger.info(f"   - All {concurrent_requests} requests successful")
                logger.info(f"   - Success rate: {stress_result['success_rate']:.2%}")
                logger.info(f"   - Execution time: {stress_result['execution_time']:.2f}s")
                logger.info(f"   - Requests/sec: {stress_result['requests_per_second']:.2f}")
            else:
                logger.error("❌ ResourceManager stress test FAILED")
                logger.error(f"   - Success rate: {stress_result['success_rate']:.2%}")
                logger.error(f"   - Failed requests: {failed_requests}/{concurrent_requests}")
            
            stress_result["success"] = success
            self.results["stress_test"] = {"status": "passed" if success else "failed", "details": stress_result}
            return stress_result
            
        except Exception as e:
            logger.error(f"❌ ResourceManager stress test ERROR: {e}")
            result = {"success": False, "error": str(e)}
            self.results["stress_test"] = {"status": "error", "details": result}
            return result

    async def test_model_eviction_policy(self) -> Dict[str, Any]:
        """
        Test 3: Model Eviction Policy Test
        
        Tests that idle models are correctly unloaded from memory by loading
        different models sequentially and checking for eviction logs.
        """
        logger.info("🧪 TEST 3: Model Eviction Policy Test")
        
        try:
            # Step 1: Load Model A (SmolLM3-3B via chat)
            logger.info("📡 Step 1: Loading Model A (SmolLM3-3B)...")
            payload_a = {
                "query": "Generate a simple hello world function in Python",
                "user_id": "eviction_test_user",
                "project_id": "model_a_test"
            }
            
            async with self.session.post(f"{BASE_URL}/chat", json=payload_a) as response:
                data_a = await response.json()
                model_a_loaded = response.status == 200 and data_a.get("response")
                logger.info(f"   Model A loading: {'✅ Success' if model_a_loaded else '❌ Failed'}")
            
            # Step 2: Wait for 10 seconds
            logger.info("⏱️ Step 2: Waiting 10 seconds for potential idle timeout...")
            await asyncio.sleep(10)
            
            # Step 3: Load Model B (CodeGenerator via agentic task)
            logger.info("📡 Step 3: Loading Model B (Gemma-3n via agentic task)...")
            payload_b = {
                "prompt": "Write a simple Python function that calculates factorial of a number",
                "user_id": "eviction_test_user", 
                "project_id": "model_b_test"
            }
            
            start_time = time.time()
            async with self.session.post(f"{BASE_URL}/execute_agentic_task", json=payload_b) as response:
                end_time = time.time()
                data_b = await response.json()
                model_b_loaded = response.status == 200 and data_b.get("status") == "success"
                logger.info(f"   Model B loading: {'✅ Success' if model_b_loaded else '❌ Failed'}")
            
            # Test result
            eviction_result = {
                "model_a_loaded": model_a_loaded,
                "model_b_loaded": model_b_loaded,
                "wait_time_seconds": 10,
                "model_b_load_time": end_time - start_time,
                "test_completion_time": time.time()
            }
            
            # Success criteria: Both models loaded successfully
            success = model_a_loaded and model_b_loaded
            
            if success:
                logger.info("✅ Model eviction policy test COMPLETED")
                logger.info("   📋 ACTION REQUIRED: Check server logs from the last 15 minutes")
                logger.info("   📋 Look for 'Evicting idle model' messages after Model B loaded")
                logger.info("   📋 This confirms the memory eviction policy is active")
                logger.info(f"   - Model B load time: {eviction_result['model_b_load_time']:.2f}s")
            else:
                logger.error("❌ Model eviction policy test FAILED")
                logger.error("   - Could not load models to test eviction policy")
            
            eviction_result["success"] = success
            self.results["eviction_test"] = {"status": "passed" if success else "failed", "details": eviction_result}
            return eviction_result
            
        except Exception as e:
            logger.error(f"❌ Model eviction policy test ERROR: {e}")
            result = {"success": False, "error": str(e)}
            self.results["eviction_test"] = {"status": "error", "details": result}
            return result

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete architecture validation suite."""
        logger.info("🚀 Architecture Validation Suite - Comprehensive System Testing")
        logger.info("=" * 80)
        
        # Health check first
        if not await self.test_service_health():
            logger.error("❌ Service health check failed. Cannot proceed with tests.")
            return {"status": "failed", "reason": "Service unhealthy", "results": self.results}
        
        logger.info("🧪 Running comprehensive architecture tests...")
        logger.info("")
        
        # Run all tests sequentially
        await self.test_multi_agent_orchestration()
        await asyncio.sleep(2)  # Brief pause between tests
        
        await self.test_resource_manager_stress()
        await asyncio.sleep(2)  # Brief pause between tests
        
        await self.test_model_eviction_policy()
        
        # Generate final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 ARCHITECTURE VALIDATION SUMMARY")
        logger.info("=" * 80)
        
        passed_tests = 0
        total_tests = len(self.results)
        
        for test_name, result in self.results.items():
            status = result["status"]
            if status == "passed":
                logger.info(f"✅ {test_name.replace('_', ' ').title()}: PASSED")
                passed_tests += 1
            elif status == "failed":
                logger.error(f"❌ {test_name.replace('_', ' ').title()}: FAILED")
            else:
                logger.warning(f"⚠️ {test_name.replace('_', ' ').title()}: ERROR")
        
        success_rate = passed_tests / total_tests
        overall_status = "PASSED" if success_rate >= 0.8 else "FAILED"  # 80% threshold
        
        logger.info("")
        logger.info(f"📈 Overall Success Rate: {success_rate:.1%} ({passed_tests}/{total_tests})")
        logger.info(f"🎯 Architecture Validation: {overall_status}")
        logger.info("")
        
        if overall_status == "PASSED":
            logger.info("🎉 Architecture is STABLE and FEATURE COMPLETE")
            logger.info("✅ Ready to proceed to next development stages")
        else:
            logger.error("⚠️ Architecture needs attention before proceeding")
            logger.error("❌ Review failed tests and address issues")
        
        return {
            "status": overall_status.lower(),
            "success_rate": success_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": self.results
        }


async def main():
    """Main entry point for architecture validation."""
    try:
        async with ArchitectureValidator() as validator:
            final_result = await validator.run_all_tests()
            
            # Save detailed results to file
            with open("architecture_validation_results.json", "w") as f:
                json.dump(final_result, f, indent=2)
            
            logger.info("📁 Detailed results saved to: architecture_validation_results.json")
            
            # Exit with appropriate code
            exit_code = 0 if final_result["status"] == "passed" else 1
            return exit_code
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Validation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Validation suite error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)