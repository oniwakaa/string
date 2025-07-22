# ModelManager Integration Guide

## Overview

The centralized ModelManager provides a single point of control for all language model loading, sharing, and lifecycle management. This solves critical memory management issues while requiring minimal changes to existing code.

## Key Benefits

✅ **Memory Management**: Automatic model eviction and memory monitoring  
✅ **Resource Sharing**: Multiple agents can share the same model instance  
✅ **Thread Safety**: Safe concurrent access to models  
✅ **Configuration Management**: Centralized model configuration  
✅ **Performance**: Model caching and intelligent loading  

## Quick Start

### 1. Initialize ModelManager

```python
from models import initialize_model_manager

# Initialize with configuration
manager = initialize_model_manager("src/models/config.json")
```

### 2. Get Models in Agents

```python
from models.integration import get_agent_model

class MyAgent:
    def __init__(self):
        # Get model through ModelManager
        self.model = get_agent_model("CodebaseExpertAgent")
        
    def process(self, prompt):
        # Use model normally
        return self.model.generate(prompt)
```

### 3. Update MemOS Integration

```python
from models.integration import get_llm_for_memos

# For project_memory_manager.py
extractor_llm_config = get_llm_for_memos(
    backend="huggingface", 
    model_path="./smollm"
)

# Use in MemOS configuration
cube_config = GeneralMemCubeConfig(
    # ... other config
    act_mem={
        "backend": "kv_cache",
        "config": {
            "memory_filename": "activation_cache.pkl",
            "extractor_llm": extractor_llm_config
        }
    }
)
```

## Migration Strategy

### Phase 1: Drop-in Replacement (Minimal Changes)

For existing agents, use the `ModelManagerAdapter`:

```python
# OLD CODE
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("./smollm")

# NEW CODE
from models.integration import create_model_adapter
adapter = create_model_adapter("CodebaseExpertAgent")
model = adapter.model  # Same interface, managed loading
```

### Phase 2: Native Integration (Recommended)

Update agents to use ModelManager directly:

```python
from models import get_model_manager

class CodebaseExpertAgent:
    def __init__(self):
        self.manager = get_model_manager()
        
    def get_model(self):
        return self.manager.get_model("SmolLM3-3B")
        
    def process(self, query):
        model = self.get_model()
        return model.generate(query)
```

## Configuration

Models are configured in `src/models/config.json`:

```json
{
  "max_memory_mb": 8192,
  "models": [
    {
      "name": "SmolLM3-3B",
      "type": "huggingface",
      "path": "./smollm",
      "context_length": 16384,
      "parameters": {
        "temperature": 0.01,
        "max_tokens": 16384,
        "do_sample": false
      },
      "memory_priority": 1,
      "max_idle_time": 300,
      "preload": true
    }
  ]
}
```

### Model Types

- **`gguf`**: GGUF models via llama-cpp-python
- **`huggingface`**: HuggingFace transformers models
- **`openai`**: OpenAI-compatible API endpoints

### Priority System

- **Priority 1**: Highest priority, last to be evicted
- **Priority 5**: Lowest priority, first to be evicted

## Memory Management

### Automatic Eviction

Models are automatically unloaded when:
- Memory limit is exceeded
- Model is idle beyond `max_idle_time`
- Higher priority models need space

### Manual Control

```python
manager = get_model_manager()

# Check memory usage
memory_info = manager.get_memory_usage()
print(f"Using {memory_info['total_mb']}MB of {memory_info['limit_mb']}MB")

# Force unload a model
manager.unload_model("model_name", force=True)

# Set memory limit
manager.set_memory_limit(4096)  # 4GB limit
```

## Integration Examples

### Updating project_memory_manager.py

```python
from models.integration import get_llm_for_memos

# In create_project_cube method, replace extractor_llm config:
"extractor_llm": get_llm_for_memos("huggingface", "./smollm")
```

### Updating Agent Classes

```python
# Before
class CodeGeneratorAgent:
    def __init__(self):
        self.model = AutoModelForCausalLM.from_pretrained("./models/gemma")
        
# After  
class CodeGeneratorAgent:
    def __init__(self):
        self.adapter = create_model_adapter("CodeGeneratorAgent")
        
    @property
    def model(self):
        return self.adapter.model
```

## Error Handling

```python
try:
    model = manager.get_model("MyModel")
except ValueError as e:
    print(f"Model not found: {e}")
except Exception as e:
    print(f"Model loading failed: {e}")
    # Use fallback model
    model = manager.get_model("SmolLM3-3B-GGUF")
```

## Best Practices

1. **Use Agent-Specific Functions**: Use `get_agent_model()` for automatic model selection
2. **Check Memory**: Monitor memory usage in production
3. **Configure Priorities**: Set appropriate memory priorities for your models
4. **Handle Failures**: Always have fallback models configured
5. **Clean Shutdown**: Call `manager.shutdown()` on application exit

## Monitoring

```python
# Get model statistics
stats = manager.get_model_stats()
for name, stat in stats.items():
    print(f"{name}: {stat.access_count} accesses, {stat.memory_usage_mb}MB")

# Register callbacks for model events
manager.register_callback('loaded', lambda name: print(f"Loaded {name}"))
manager.register_callback('evicted', lambda name: print(f"Evicted {name}"))
```

## Next Steps

1. **Initialize**: Set up ModelManager in your main application
2. **Configure**: Update `src/models/config.json` with your models
3. **Integrate**: Update agents to use ModelManager
4. **Test**: Verify memory usage and performance
5. **Monitor**: Track model loading and eviction in production

The ModelManager is designed for minimal disruption - you can migrate incrementally while gaining immediate memory management benefits.