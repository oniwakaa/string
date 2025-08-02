#!/usr/bin/env python3
"""
Test Core Logic for /clear and /compact Functions

This script validates the clear_workspace_context() and compact_workspace_context()
functions to ensure they properly interface with MemOS and provide the expected
functionality for workspace management.

Run within the activated virtual environment:
source venv/bin/activate && python test_core_logic.py
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.codebase_state_manager import CodebaseStateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockMemCube:
    """Mock MemOS memory cube for testing"""
    def __init__(self, cube_id: str):
        self.cube_id = cube_id
        self.memories = []
        self.text_mem = self
    
    def get_all(self):
        return self.memories
    
    def delete_all(self):
        self.memories.clear()
        
    def add(self, content: str, metadata: Dict = None):
        memory = {
            'content': content,
            'metadata': metadata or {}
        }
        self.memories.append(memory)

class MockMOS:
    """Mock MemOS instance for testing"""
    def __init__(self):
        self.mem_cubes = {
            'chat_history': MockMemCube('chat_history'),
            'codebase_context': MockMemCube('codebase_context')
        }
        self.user_id = "test_user"
        
        # Populate with test data
        self._populate_test_data()
    
    def _populate_test_data(self):
        """Populate with test chat history"""
        test_messages = [
            "User: How do I implement a REST API in Python?",
            "Assistant: You can implement a REST API in Python using FastAPI. Here's a comprehensive example with endpoints for CRUD operations, error handling, request validation, response models, dependency injection, middleware, background tasks, and proper documentation generation. FastAPI automatically generates OpenAPI documentation and provides interactive API docs. You'll need to install FastAPI and Uvicorn, create your main application file, define your data models using Pydantic, set up your routes with proper HTTP methods, implement database connectivity, add authentication and authorization, configure CORS if needed, and deploy your application to production environments.",
            "User: Can you show me how to add JWT authentication to this API?",
            "Assistant: Sure! Here's how to add JWT authentication to your FastAPI application using python-jose and passlib libraries. First, install the required dependencies: pip install python-jose[cryptography] passlib[bcrypt] python-multipart. Then create a security utility module with password hashing functions, JWT token creation and verification, user authentication logic, and token validation middleware. Set up authentication routes for login and registration, protect your API endpoints with dependency injection, handle token expiration and refresh, implement role-based access control, secure sensitive routes, and ensure proper error handling for authentication failures.",
            "User: What about database integration with SQLAlchemy and PostgreSQL?",
            "Assistant: For database integration, you can use SQLAlchemy with FastAPI and PostgreSQL. Here's a complete example with models, database connection, and CRUD operations. Install the required packages: pip install sqlalchemy psycopg2-binary alembic. Set up your database configuration with connection strings, create SQLAlchemy models with proper relationships, implement database session management with dependency injection, create repository patterns for data access, set up database migrations with Alembic, implement connection pooling for performance, add database transaction handling, create proper indexing strategies, implement data validation and constraints, and set up database monitoring and logging.",
            "User: How do I handle file uploads and implement caching?",
            "Assistant: FastAPI provides excellent support for file uploads and caching mechanisms. For file uploads, you can use the File and UploadFile types from fastapi. Create endpoints that accept multipart form data, validate file types and sizes, implement secure file storage with proper naming conventions, handle large file uploads with streaming, add virus scanning capabilities, implement file compression and optimization, create thumbnail generation for images, and set up cleanup procedures for temporary files. For caching, implement Redis integration, create cache decorators, implement cache invalidation strategies, set up cache warming procedures, monitor cache hit rates, and implement distributed caching for scalability.",
            "User: Can you explain async/await patterns and performance optimization?",
            "Assistant: Async/await in FastAPI allows you to handle concurrent requests efficiently and improve application performance significantly. Here's how it works with database operations, external API calls, and I/O operations. Implement proper async database connections using async SQLAlchemy or asyncpg, create async route handlers for non-blocking operations, use async context managers for resource management, implement connection pooling for database efficiency, add request/response middleware for monitoring, create background task processing with Celery or FastAPI background tasks, implement rate limiting and throttling, add request timeout handling, create proper logging and monitoring, optimize serialization and deserialization, implement response compression, and set up load balancing and scaling strategies.",
            "User: What are the best practices for testing and deployment?",
            "Assistant: For testing FastAPI applications, implement comprehensive test suites using pytest and httpx. Create unit tests for individual functions, integration tests for API endpoints, end-to-end tests for complete workflows, database tests with test fixtures, authentication tests with mock users, performance tests for load testing, and security tests for vulnerability assessment. Set up test databases, implement test data factories, create mock services for external dependencies, and establish continuous integration pipelines. For deployment, use Docker containers for consistency, implement blue-green deployments for zero downtime, set up monitoring with Prometheus and Grafana, configure logging aggregation, implement health checks and readiness probes, set up auto-scaling policies, configure SSL certificates, implement CDN for static content, and establish backup and disaster recovery procedures."
        ]
        
        for i, message in enumerate(test_messages):
            self.mem_cubes['chat_history'].add(message, {'message_id': i, 'timestamp': f'2025-01-{i+1:02d}'})
    
    def get_all(self, mem_cube_id: str, user_id: str = None):
        """Get all memories from a cube"""
        if mem_cube_id in self.mem_cubes:
            memories = self.mem_cubes[mem_cube_id].get_all()
            return [{'cube_id': mem_cube_id, 'memories': memories}]
        return []
    
    def delete_all(self, mem_cube_id: str, user_id: str = None):
        """Delete all memories from a cube"""
        if mem_cube_id in self.mem_cubes:
            self.mem_cubes[mem_cube_id].delete_all()
    
    def add(self, mem_cube_id: str, user_id: str, content: str, metadata: Dict = None):
        """Add a memory to a cube"""
        if mem_cube_id in self.mem_cubes:
            self.mem_cubes[mem_cube_id].add(content, metadata)
    
    def clear(self):
        """Clear all memory cubes"""
        self.mem_cubes.clear()

class MockLLMService:
    """Mock LLM service for testing summarization"""
    
    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        """Generate a mock summary"""
        # Simulate LLM summarization
        if "REST API" in prompt and "authentication" in prompt:
            return ("Discussion covered REST API implementation in Python using FastAPI, "
                   "JWT authentication setup, SQLAlchemy database integration, "
                   "file upload handling, and async/await patterns for concurrent requests.")
        else:
            return "General technical discussion about Python development topics."

def test_clear_workspace_context():
    """Test the clear_workspace_context function"""
    logger.info("🧪 Testing clear_workspace_context function...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CodebaseStateManager
        state_manager = CodebaseStateManager(temp_dir)
        
        # Create mock MemOS instance with test data
        mock_mos = MockMOS()
        
        # Verify initial state - should have test data
        initial_chat_count = len(mock_mos.get_all('chat_history'))
        initial_cube_count = len(mock_mos.mem_cubes)
        
        logger.info(f"Initial state: {initial_chat_count} chat messages, {initial_cube_count} memory cubes")
        assert initial_chat_count > 0, "Should have initial test data"
        assert initial_cube_count > 0, "Should have initial memory cubes"
        
        # Test clear operation
        result = state_manager.clear_workspace_context("test_workspace", mock_mos)
        
        # Validate results
        assert result["success"] is True, "Clear operation should succeed"
        assert result["workspace_id"] == "test_workspace", "Should return correct workspace ID"
        assert "cleared_components" in result, "Should list cleared components"
        
        # Verify MemOS state after clearing
        post_clear_chat_count = len(mock_mos.get_all('chat_history'))
        post_clear_cube_count = len(mock_mos.mem_cubes)
        
        logger.info(f"Post-clear state: {post_clear_chat_count} chat messages, {post_clear_cube_count} memory cubes")
        assert post_clear_chat_count == 0, "Chat history should be empty after clear"
        assert post_clear_cube_count == 0, "Memory cubes should be cleared"
        
        logger.info("✅ clear_workspace_context test PASSED")
        return True

def test_compact_workspace_context():
    """Test the compact_workspace_context function"""
    logger.info("🧪 Testing compact_workspace_context function...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CodebaseStateManager
        state_manager = CodebaseStateManager(temp_dir)
        
        # Create mock MemOS instance with test data
        mock_mos = MockMOS()
        mock_llm = MockLLMService()
        
        # Verify initial state
        initial_chat_history = state_manager._get_chat_history_from_memos("test_workspace", mock_mos)
        initial_token_count = sum(len(msg.split()) for msg in initial_chat_history)
        
        logger.info(f"Initial state: {len(initial_chat_history)} messages, ~{initial_token_count} tokens")
        assert len(initial_chat_history) > 0, "Should have initial chat history"
        assert initial_token_count >= 500, f"Should have at least 500 tokens for compression test (got {initial_token_count})"
        
        # Test compact operation
        result = state_manager.compact_workspace_context("test_workspace", mock_llm, mock_mos)
        
        # Validate results
        assert result["success"] is True, "Compact operation should succeed"
        assert result["workspace_id"] == "test_workspace", "Should return correct workspace ID"
        assert result["original_length"] > 0, "Should report original length"
        assert result["compressed_length"] > 0, "Should report compressed length"
        assert result["compression_ratio"] > 0, "Should achieve compression"
        
        # Verify compression achieved at least 30% reduction
        compression_ratio = result["compression_ratio"]
        logger.info(f"Compression achieved: {compression_ratio:.1%} reduction")
        assert compression_ratio >= 0.3, f"Should achieve at least 30% compression (got {compression_ratio:.1%})"
        
        # Verify MemOS state after compaction
        post_compact_history = state_manager._get_chat_history_from_memos("test_workspace", mock_mos)
        post_compact_tokens = sum(len(msg.split()) for msg in post_compact_history)
        
        logger.info(f"Post-compact state: {len(post_compact_history)} messages, ~{post_compact_tokens} tokens")
        assert len(post_compact_history) > 0, "Should have summary after compaction"
        assert post_compact_tokens < initial_token_count, "Token count should be reduced"
        
        logger.info("✅ compact_workspace_context test PASSED")
        return True

def test_compact_empty_history():
    """Test compact function with empty history"""
    logger.info("🧪 Testing compact_workspace_context with empty history...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CodebaseStateManager
        state_manager = CodebaseStateManager(temp_dir)
        
        # Create empty mock MemOS instance
        mock_mos = MockMOS()
        mock_mos.mem_cubes.clear()  # Start with empty cubes
        mock_llm = MockLLMService()
        
        # Test compact operation on empty history
        result = state_manager.compact_workspace_context("empty_workspace", mock_llm, mock_mos)
        
        # Validate results
        assert result["success"] is True, "Compact operation should succeed even with empty history"
        assert result["original_length"] == 0, "Should report zero original length"
        assert result["compressed_length"] == 0, "Should report zero compressed length"
        assert result["compression_ratio"] == 0.0, "Should report zero compression ratio"
        assert result["message"] == "No chat history to compact", "Should report no history message"
        
        logger.info("✅ compact_workspace_context (empty history) test PASSED")
        return True

def test_without_memos():
    """Test functions without MemOS instance"""
    logger.info("🧪 Testing functions without MemOS instance...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CodebaseStateManager
        state_manager = CodebaseStateManager(temp_dir)
        
        # Test clear without MemOS
        clear_result = state_manager.clear_workspace_context("test_workspace", None)
        assert clear_result["success"] is True, "Clear should succeed without MemOS (file cleanup only)"
        
        # Test compact without MemOS
        compact_result = state_manager.compact_workspace_context("test_workspace", None, None)
        assert compact_result["success"] is True, "Compact should succeed with empty history"
        assert compact_result["original_length"] == 0, "Should report zero length without MemOS"
        
        logger.info("✅ Functions without MemOS test PASSED")
        return True

def main():
    """Run all tests"""
    logger.info("🚀 Starting Core Logic Tests for /clear and /compact functions")
    logger.info("=" * 70)
    
    tests = [
        test_clear_workspace_context,
        test_compact_workspace_context,
        test_compact_empty_history,
        test_without_memos
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            logger.info(f"✅ {test_func.__name__} PASSED")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("-" * 50)
    
    # Summary
    logger.info("=" * 70)
    logger.info("🎯 TEST SUMMARY")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 All tests PASSED! Core logic is ready for API integration.")
        return 0
    else:
        logger.error("💥 Some tests FAILED! Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)