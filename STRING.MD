# AI Coding Assistant - Project Context & Preferences

This file contains project-specific context, preferences, and guidelines that should influence all AI-generated code and responses in this codebase.

## Project Overview

This is a **local, multi-agent AI coding assistant** designed to rival commercial tools like Cursor while running entirely offline on Apple Silicon devices. The system uses GGUF-quantized models for efficiency and maintains project-specific memory through MemOS.

## Core Principles

### 1. Local-First Architecture
- **No Cloud Dependencies**: All models, processing, and data storage must remain local
- **Privacy by Design**: No external API calls for core functionality
- **Offline Capable**: System should work without internet connectivity

### 2. Performance Optimization
- **Memory Efficiency**: Target <8GB RAM usage for compatibility with 16GB systems
- **Apple Silicon**: Leverage Metal Performance Shaders for GPU acceleration
- **Response Time**: Maintain <6 second average response times for multi-agent workflows

### 3. Multi-Agent Design
- **Specialized Agents**: Each agent has a specific role (code generation, quality analysis, etc.)
- **Orchestrated Workflows**: Complex tasks are decomposed and delegated appropriately
- **Project Context**: All agents should have access to project-specific preferences and memory

## Code Style & Standards

### Python Development
- **Type Hints**: Always use comprehensive type hints for function signatures
- **Docstrings**: Follow Google-style docstrings for all public methods
- **Error Handling**: Implement comprehensive try-catch blocks with meaningful error messages
- **Logging**: Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Architecture Patterns
- **Dependency Injection**: Use dependency injection for testability and modularity
- **Resource Management**: Implement proper cleanup and resource disposal
- **Configuration**: Use centralized configuration with environment variable overrides
- **Testing**: Maintain high test coverage with both unit and integration tests

## Technology Stack Preferences

### Core Technologies
- **FastAPI**: For API endpoints and service architecture
- **Pydantic**: For data validation and serialization
- **AsyncIO**: For asynchronous operations and concurrency
- **llama-cpp-python**: For GGUF model inference
- **Qdrant**: For vector storage and semantic search

### Development Tools
- **Poetry**: For dependency management and virtual environments
- **pytest**: For testing framework
- **Black**: For code formatting (though not enforced)
- **mypy**: For static type checking

## Project-Specific Guidelines

### MemOS Integration
- **Memory Isolation**: Maintain separate memory contexts per project
- **Incremental Loading**: Only reload changed files during codebase updates
- **Context Optimization**: Prioritize relevant code context over comprehensive coverage

### Agent Orchestration
- **Task Decomposition**: Break complex requests into manageable subtasks
- **Context Sharing**: Pass relevant project preferences to all agents
- **Error Recovery**: Implement graceful fallbacks for agent failures

### Model Management
- **Lazy Loading**: Load models only when needed to conserve memory
- **Resource Sharing**: Share model instances across agents when possible
- **GPU Utilization**: Optimize for Metal on Apple Silicon, CUDA on NVIDIA systems

## Quality Standards

### Code Generation
- **Functional First**: Prioritize working code over perfect code
- **Incremental Improvement**: Suggest refactoring opportunities after basic functionality
- **Security Awareness**: Avoid generating code with obvious security vulnerabilities
- **Performance Consideration**: Be mindful of computational complexity

### Documentation
- **Self-Documenting Code**: Write clear, readable code that explains its purpose
- **API Documentation**: Maintain up-to-date API documentation
- **Usage Examples**: Provide practical examples for complex functionality
- **Change Logs**: Document significant changes and their rationale

## User Experience

### CLI Interface Design
- **Intuitive Commands**: Use clear, self-explanatory command names
- **Helpful Output**: Provide informative status messages and error descriptions
- **Progress Indicators**: Show progress for long-running operations
- **Graceful Degradation**: Handle edge cases without crashing

### Response Quality
- **Contextual Awareness**: Consider the existing codebase when making suggestions
- **Consistent Style**: Match the established patterns and conventions
- **Practical Solutions**: Focus on implementable, tested solutions
- **Clear Communication**: Explain reasoning behind suggestions when helpful

## Integration Preferences

### External Services
- **Ollama**: For web research models and additional language model support
- **HuggingFace**: For model downloads and updates (when internet available)
- **Git**: For version control integration and change tracking

### File Management
- **Memignore System**: Respect .memignore patterns for codebase filtering
- **State Tracking**: Maintain file change detection for intelligent loading
- **Backup Strategy**: Preserve important configurations and state files

---

**Note**: These preferences should be treated as guidelines that influence decision-making, not rigid rules. Context and practicality should always take precedence when these guidelines conflict with specific requirements or constraints.