# Full Stack Integration Test Suite

This directory contains comprehensive integration tests that validate the entire AI coding assistant pipeline through real-world developer workflows.

## Overview

The integration test suite simulates sophisticated user interactions with the multi-agent system, validating:

- **Agent Orchestration**: Correct agent selection and task decomposition
- **MemOS Integration**: RAG retrieval and codebase context injection  
- **Code Generation**: Quality of generated code and API skeletons
- **Code Modification**: Precise editing and refactoring capabilities
- **Terminal Operations**: File system operations and shell command execution
- **Error Handling**: Graceful failure recovery and user feedback
- **Performance**: Latency, memory usage, and resource efficiency

## Test Workflows

### 1. REST API Creation
**Scenario**: "Create a Python REST API skeleton with health check endpoint"
- **Validates**: Intent classification, CodeGeneratorAgent, file creation
- **Expected**: FastAPI/Flask skeleton with `/health` endpoint

### 2. Metrics Endpoint Addition  
**Scenario**: "Add a /metrics endpoint that returns simulated stats"
- **Validates**: Code modification, integration with existing code
- **Expected**: `/metrics` endpoint with system statistics

### 3. Codebase Search
**Scenario**: "Find all function definitions related to logging in the current codebase"
- **Validates**: MemOS RAG, CodebaseExpertAgent, search functionality
- **Expected**: List of logging-related functions with file locations

### 4. Code Refactoring
**Scenario**: "Refactor the health check to include uptime and memory info"
- **Validates**: CodeEditorAgent precision, quality improvements
- **Expected**: Enhanced health check with additional metrics

### 5. Test Execution
**Scenario**: "Run the unit tests and show me the results"
- **Validates**: ToolExecutorAgent, terminal command execution
- **Expected**: Test results and output capture

### 6. Server Operations
**Scenario**: "Start the development server"
- **Validates**: Process management, confirmation system
- **Expected**: Server management commands (simulated in tests)

### 7. Error Detection
**Scenario**: Intentional code errors with analysis request
- **Validates**: Error handling, CodeQualityAgent, recovery mechanisms
- **Expected**: Error detection and diagnostic feedback

## Running the Tests

### Prerequisites

1. **Backend Service**: Start the service first
   ```bash
   python run_gguf_service.py
   ```

2. **Models**: Ensure all GGUF models are downloaded
   ```bash
   scripts/get_models.sh  # If available
   ```

3. **Dependencies**: Install test dependencies
   ```bash
   poetry install
   pip install pytest psutil httpx
   ```

### Quick Start

Use the test runner script for best experience:

```bash
# Run with server health check and cleanup
python run_integration_tests.py --server-check --cleanup

# Run with custom workspace
python run_integration_tests.py --workspace-dir ./custom_test_workspace

# Generate report from previous run
python run_integration_tests.py --report-only
```

### Direct Pytest Execution

```bash
# Run all integration tests
pytest tests/integration/full_stack_pipeline_test.py -v -s

# Run specific test workflow
pytest tests/integration/full_stack_pipeline_test.py::TestFullStackPipeline::test_workflow_1_rest_api_creation -v

# Run with custom environment
WORKSPACE_ROOT=./my_workspace pytest tests/integration/full_stack_pipeline_test.py -v
```

## Test Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKSPACE_ROOT` | Test workspace directory | `./test_workspace` |
| `QDRANT_STORAGE` | Qdrant storage path | `./qdrant_storage` |
| `TEST_SERVER_URL` | Backend service URL | `http://127.0.0.1:8000` |

### Pytest Configuration

The test suite uses these pytest configurations:

- **Markers**: `integration`, `slow`, `requires_server`
- **Logging**: Detailed CLI logging for debugging
- **Timeout**: 30 seconds per test method
- **Output**: Live output capture for monitoring

## Performance Monitoring

The test suite includes comprehensive performance monitoring:

### Metrics Tracked
- **Execution Time**: Per-operation and total latency
- **Memory Usage**: RSS and VMS memory consumption  
- **CPU Usage**: Process CPU utilization
- **Resource Peaks**: Maximum memory and CPU usage

### Performance Reports

After test completion, detailed performance reports are generated:

```json
{
  "performance_summary": {
    "total_operations": 7,
    "total_time_seconds": 45.2,
    "max_memory_mb": 156.8,
    "average_cpu_percent": 12.3
  }
}
```

## Test Architecture

### Test Components

1. **PerformanceMonitor**: System resource tracking
2. **TestWorkspaceManager**: Clean test environment setup
3. **TestFullStackPipeline**: Main test class with workflow validation
4. **Agent Simulators**: Mock agent execution for isolated testing

### Workspace Management

Each test run creates a clean workspace:

```
test_workspace_20250126_143052/
├── src/
│   └── utils.py          # Sample module with known functions
├── tests/
│   └── test_utils.py     # Sample unit tests
├── docs/
└── README.md             # Project documentation
```

### Agent Simulation

For reliable testing, agent execution is simulated but realistic:

- **CodeGeneratorAgent**: Generates actual API code
- **CodeEditorAgent**: Performs real file modifications
- **CodebaseExpertAgent**: Searches actual workspace files
- **ToolExecutorAgent**: Executes real system commands (safely)
- **CodeQualityAgent**: Analyzes actual code quality

## Error Handling

The test suite validates comprehensive error handling:

### Simulated Error Conditions
- Syntax errors in generated code
- Missing dependencies
- File permission issues
- Network connectivity problems
- Agent execution failures

### Recovery Validation
- Graceful degradation
- User-friendly error messages
- Retry mechanisms
- Fallback strategies

## Continuous Integration

### CI Configuration

For CI/CD pipelines, use these configurations:

```yaml
# GitHub Actions example
- name: Run Integration Tests
  run: |
    python run_gguf_service.py &
    sleep 10  # Wait for service startup
    python run_integration_tests.py --server-check --cleanup
  env:
    WORKSPACE_ROOT: ${{ github.workspace }}/test_workspace
```

### Performance Benchmarks

Recommended performance thresholds:

| Metric | Target | Acceptable |
|--------|--------|------------|
| Total Test Time | < 60s | < 120s |
| Max Memory Usage | < 200MB | < 400MB |
| Agent Response Time | < 5s | < 10s |
| Success Rate | 100% | ≥ 95% |

## Troubleshooting

### Common Issues

1. **Service Not Running**
   ```
   ❌ Backend service is not available
   ```
   **Solution**: Start the backend service first

2. **Workspace Permission Errors**
   ```
   ❌ Permission denied: test_workspace
   ```
   **Solution**: Ensure write permissions or use custom workspace

3. **Model Loading Failures**
   ```
   ❌ Model not found: SmolLM3-3B
   ```
   **Solution**: Download models using setup scripts

4. **Memory Issues**
   ```
   ❌ Out of memory during test execution
   ```
   **Solution**: Close other applications or increase system memory

### Debug Mode

Enable detailed logging for debugging:

```bash
# Set debug logging level
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
" && pytest tests/integration/full_stack_pipeline_test.py -v -s --log-cli-level=DEBUG
```

### Test Isolation

Each test method is isolated:
- Clean workspace per test session
- Fresh agent instances
- Independent performance monitoring
- Separate error handling

## Contributing

When adding new test workflows:

1. **Follow Naming Convention**: `test_workflow_N_description`
2. **Add Performance Monitoring**: Use `monitor.start_monitoring()`
3. **Include Assertions**: Validate expected outcomes
4. **Update Documentation**: Add workflow description
5. **Test Error Cases**: Include failure scenarios

### Test Template

```python
@pytest.mark.asyncio
async def test_workflow_N_new_feature(self, test_environment):
    """
    Workflow N: Description of the workflow
    
    Validates:
    - What this test validates
    - Expected agent behavior
    - Performance characteristics
    """
    monitor = test_environment['monitor']
    monitor.start_monitoring("New Feature Test")
    
    prompt = "User prompt for the workflow"
    
    # Execute workflow
    plan = await self.project_manager._decompose_prompt(prompt)
    
    # Validate plan
    assert len(plan) > 0, "Should generate execution plan"
    
    # Execute and validate results
    # ... test implementation
    
    monitor.capture_metrics()
    
    # Assert expected outcomes
    assert expected_condition, "Should meet expected outcome"
    
    logger.info("✅ Workflow N completed: New feature validated")
```

## Support

For issues with the integration test suite:

1. Check the [troubleshooting section](#troubleshooting)
2. Review test logs in `tests/integration/full_stack_test.log`
3. Examine the performance report in `tests/integration/test_report.json`
4. Run with debug logging for detailed output

The integration test suite ensures the AI coding assistant meets production-quality standards for real-world developer workflows.