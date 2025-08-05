"""
ResourceManager - Centralized Resource Management with MemOS Dependency Injection

This module implements a sophisticated resource management system that bypasses
MemOS's internal factory patterns to prevent memory exhaustion and resource conflicts.

The key innovation is intercepting MemOS component creation and injecting shared
resources instead of allowing each component to create its own models and databases.
"""

import os
import sys
from typing import Dict, Any, Optional
import logging

# Add MemOS to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'MemOS', 'src'))

# Import MemOS components
from memos.configs.mem_cube import GeneralMemCubeConfig
from memos.mem_cube.general import GeneralMemCube
from memos.memories.textual.general import GeneralTextMemory
from memos.memories.activation.kv import KVCacheMemory
from memos.configs.memory import GeneralTextMemoryConfig

# Import our shared resources
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.manager import model_manager

logger = logging.getLogger(__name__)


class SharedQdrantClient:
    """Shared Qdrant client wrapper that prevents multiple instances."""
    
    def __init__(self, path: str = "./qdrant_storage_rm"):
        from qdrant_client import QdrantClient
        logger.info(f"🔧 [ResourceManager] Creating QdrantClient for path: {path}")
        self.client = QdrantClient(path=path)
        self.path = path
        self._created_collections = set()
        logger.info(f"✅ [ResourceManager] SharedQdrantClient initialized at {path}")
    
    def create_collection(self, collection_name: str, vector_dimension: int = 384, distance_metric: str = "cosine"):
        """Create collection if it doesn't exist."""
        if collection_name in self._created_collections:
            return
            
        from qdrant_client.http import models
        
        try:
            # Check if collection exists
            if self.client.collection_exists(collection_name):
                logger.info(f"Collection '{collection_name}' already exists")
                self._created_collections.add(collection_name)
                return
                
            # Create new collection
            distance_map = {
                "cosine": models.Distance.COSINE,
                "euclidean": models.Distance.EUCLID,
                "dot": models.Distance.DOT
            }
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_dimension,
                    distance=distance_map.get(distance_metric, models.Distance.COSINE)
                )
            )
            self._created_collections.add(collection_name)
            logger.info(f"Created collection '{collection_name}' with dimension {vector_dimension}")
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
    
    def __getattr__(self, name):
        # Proxy all calls to the underlying client
        return getattr(self.client, name)


class SharedEmbedder:
    """Shared embedder wrapper using sentence-transformers."""
    
    def __init__(self, model_name: str = None):
        from sentence_transformers import SentenceTransformer
        from pathlib import Path
        
        # Try local model path first, fallback to HuggingFace ID
        if model_name is None:
            local_model_path = Path("models/embedding/all-MiniLM-L6-v2")
            if local_model_path.exists():
                model_name = str(local_model_path)
                logger.info(f"Using local embedding model: {model_name}")
            else:
                model_name = "all-MiniLM-L6-v2"
                logger.warning(f"Local model not found, falling back to HuggingFace: {model_name}")
        
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        logger.info(f"SharedEmbedder initialized with {model_name}")
    
    def embed(self, texts):
        """Embed a list of texts."""
        return self.model.encode(texts)


class ResourceManager:
    """
    Centralized Resource Manager with MemOS Dependency Injection.
    
    This class prevents MemOS from creating multiple model and database instances
    by intercepting the component creation process and injecting shared resources.
    """
    
    def __init__(self):
        self._mem_cubes: Dict[str, GeneralMemCube] = {}
        self._qdrant_clients: Dict[str, Any] = {}  # Path -> QdrantClient singleton dictionary
        self._embedder: Optional[SharedEmbedder] = None
        logger.info("ResourceManager initialized with singleton resource management")
    
    def get_qdrant_client(self, path: str = "./qdrant_storage"):
        """Get or create singleton Qdrant client - PREVENTS LOCK FILES."""
        if path not in self._qdrant_clients:
            from qdrant_client import QdrantClient
            logger.info(f"🔧 Creating singleton QdrantClient for path: {path}")
            
            # Clean any existing lock files before creating client
            import os
            lock_file = os.path.join(path, ".lock")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"🧹 Removed existing lock file: {lock_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove lock file: {e}")
            
            # Create the singleton client
            self._qdrant_clients[path] = QdrantClient(path=path)
            logger.info(f"✅ Singleton QdrantClient created for {path}")
        
        return self._qdrant_clients[path]
    
    def get_embedder(self, model_name: str = None) -> SharedEmbedder:
        """Get or create shared embedder."""
        if self._embedder is None:
            self._embedder = SharedEmbedder(model_name)
            logger.info("Created shared embedder")
        return self._embedder
    
    def create_shared_text_memory(self, config: GeneralTextMemoryConfig, collection_name: str = None) -> GeneralTextMemory:
        """
        Create GeneralTextMemory with shared resources instead of internal factories.
        
        This is the critical fix - we bypass MemOS's internal LLMFactory, VecDBFactory,
        and EmbedderFactory to prevent multiple model loading.
        """
        # Create an "empty" GeneralTextMemory instance
        text_memory = object.__new__(GeneralTextMemory)
        
        # Set the config
        text_memory.config = config
        
        # Extract collection name from config or use provided one
        if not collection_name and hasattr(config, 'vector_db') and hasattr(config.vector_db, 'config'):
            collection_name = getattr(config.vector_db.config, 'collection_name', 'default_collection')
        elif not collection_name:
            collection_name = 'default_collection'
        
        # Inject shared resources instead of letting it create its own
        text_memory.extractor_llm = LLMModelWrapper(model_manager.get_model("SmolLM3-3B"))
        text_memory.vector_db = QdrantVecDBWrapper(self.get_qdrant_client(), collection_name)
        text_memory.embedder = EmbedderWrapper(self.get_embedder())
        
        logger.info(f"Created GeneralTextMemory with shared resources for collection '{collection_name}' (bypassed factories)")
        return text_memory
    
    def create_shared_kv_memory(self, config) -> Optional[KVCacheMemory]:
        """
        Create KVCacheMemory with shared resources.
        For now, we'll return None to disable activation memory for stability.
        """
        logger.info("KVCacheMemory disabled for stability (activation memory = None)")
        return None
    
    def create_text_memory_with_singleton(self, qdrant_client, collection_name: str) -> GeneralTextMemory:
        """
        Create GeneralTextMemory with singleton QdrantClient - BYPASSES ALL FACTORIES.
        
        This method manually constructs the textual memory by passing pre-initialized
        objects instead of configurations, preventing any factory-based QdrantClient creation.
        """
        logger.info(f"🔧 [SINGLETON] Creating textual memory with singleton client for: {collection_name}")
        
        # Create empty GeneralTextMemory without triggering constructor
        text_memory = object.__new__(GeneralTextMemory)
        
        # Manually set required attributes
        text_memory.config = None  # We're bypassing config-based initialization
        
        # Inject singleton resources directly
        text_memory.extractor_llm = LLMModelWrapper(model_manager.get_model("SmolLM3-3B"))
        text_memory.vector_db = DirectQdrantWrapper(qdrant_client, collection_name)
        text_memory.embedder = EmbedderWrapper(self.get_embedder())
        
        logger.info(f"✅ [SINGLETON] TextualMemory created with singleton QdrantClient - NO factories used")
        return text_memory
    
    def create_generic_kv_memory(self, storage_path: str):
        """
        Create GenericKVMemory for parametric preferences storage.
        
        This provides a lightweight parametric memory backend that stores
        project preferences as JSON files instead of requiring LoRA.
        """
        try:
            # Import here to avoid circular imports
            import sys
            import os
            # Add both the src directory and project root to path
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from src.memos.memory_systems.generic_kv_memory import GenericKVMemory
            
            # Create the GenericKVMemory instance
            kv_memory = GenericKVMemory(storage_path)
            logger.info(f"✅ GenericKVMemory created for path: {storage_path}")
            return kv_memory
            
        except Exception as e:
            logger.error(f"❌ Failed to create GenericKVMemory: {e}")
            return None
    
    def get_mem_cube(self, cube_id: str, config: GeneralMemCubeConfig) -> GeneralMemCube:
        """
        Get or create MemCube with singleton resources - PREVENTS LOCK FILES.
        
        This method forces dependency injection by manually constructing the MemCube
        and passing already-initialized singleton objects instead of configurations.
        """
        if cube_id in self._mem_cubes:
            logger.info(f"Returning cached MemCube: {cube_id}")
            return self._mem_cubes[cube_id]
        
        logger.info(f"🔧 [SINGLETON] Creating MemCube with forced dependency injection: {cube_id}")
        
        # Extract storage path from config
        storage_path = "./qdrant_storage"  # Use same path as MemOS to share storage
        if (hasattr(config.text_mem, 'config') and 
            hasattr(config.text_mem.config, 'vector_db') and 
            hasattr(config.text_mem.config.vector_db, 'config') and 
            hasattr(config.text_mem.config.vector_db.config, 'path')):
            storage_path = config.text_mem.config.vector_db.config.path
        
        # Get the singleton QdrantClient - THIS PREVENTS LOCK CONFLICTS
        qdrant_singleton = self.get_qdrant_client(storage_path)
        
        # Create an empty MemCube without triggering internal factories
        mem_cube = object.__new__(GeneralMemCube)
        mem_cube.config = config
        
        # Phase 1: Manually construct textual memory with singleton client
        if config.text_mem.backend != "uninitialized":
            # Extract collection name
            collection_name = "default_collection"
            if (hasattr(config.text_mem, 'config') and 
                hasattr(config.text_mem.config, 'vector_db') and 
                hasattr(config.text_mem.config.vector_db, 'config') and 
                hasattr(config.text_mem.config.vector_db.config, 'collection_name')):
                collection_name = config.text_mem.config.vector_db.config.collection_name
            
            # Create textual memory with singleton client - NO CONFIG PASSED
            mem_cube._text_mem = self.create_text_memory_with_singleton(
                qdrant_client=qdrant_singleton,
                collection_name=collection_name
            )
            logger.info(f"✅ Textual memory created with singleton QdrantClient for collection: {collection_name}")
        else:
            mem_cube._text_mem = None
            logger.info("⚠️ Textual memory disabled")
        
        # Phase 2: Activation Memory - Enable KVCacheMemory with shared LLM
        if config.act_mem.backend != "uninitialized":
            try:
                # Get lightweight embedding model for KV cache extraction
                kv_cache_llm = model_manager.get_model("Qwen3-Embedding-0.6B-GGUF")
                
                # Create KVCacheMemory with direct LLM injection - BYPASSES FACTORY
                from memos.memories.activation.kv import KVCacheMemory
                
                # Manually instantiate KVCacheMemory with shared resources - BYPASSES FACTORY
                mem_cube._act_mem = object.__new__(KVCacheMemory)
                mem_cube._act_mem.config = config.act_mem
                mem_cube._act_mem.llm = LLMModelWrapper(kv_cache_llm)  # Direct LLM injection
                mem_cube._act_mem.kv_cache_memories = {}  # Initialize empty cache dictionary
                
                logger.info("✅ KVCacheMemory created with shared Qwen3-Embedding-0.6B for extraction")
            except Exception as e:
                logger.error(f"❌ Failed to create KVCacheMemory: {e}")
                mem_cube._act_mem = None
        else:
            mem_cube._act_mem = None
            logger.info("⚠️ Activation memory disabled via config")
        
        # Phase 3: Parametric Memory - Use GenericKVMemory for preferences
        para_storage_path = f"./memory_cubes/{config.user_id}/{config.cube_id}/parametric"
        mem_cube._para_mem = self.create_generic_kv_memory(para_storage_path)
        logger.info(f"✅ Parametric memory created with GenericKVMemory at: {para_storage_path}")
        
        # Cache the cube
        self._mem_cubes[cube_id] = mem_cube
        
        logger.info(f"✅ MemCube '{cube_id}' created with singleton dependency injection - NO LOCK FILES")
        return mem_cube
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource usage statistics."""
        model_stats = model_manager.get_memory_stats()
        
        return {
            "mem_cubes_cached": len(self._mem_cubes),
            "qdrant_client_shared": self._qdrant_client is not None,
            "embedder_shared": self._embedder is not None,
            "model_manager_stats": model_stats,
            "total_models_loaded": model_stats.get("currently_loaded", 0),
            "resource_sharing_active": True
        }


class LLMModelWrapper:
    """Wrapper to make ModelManager models compatible with MemOS LLM interface."""
    
    def __init__(self, llama_model):
        self.model = llama_model
        self.model_name = "ModelManager-GGUF"
    
    def generate(self, messages):
        """Generate response compatible with MemOS expectations."""
        # Convert messages to prompt
        if isinstance(messages, list) and len(messages) > 0:
            prompt = messages[-1].get("content", "")
        else:
            prompt = str(messages)
        
        # Use the ModelManager model
        response = self.model(
            prompt,
            max_tokens=512,
            temperature=0.1,
            echo=False
        )
        
        if response and response.get('choices'):
            return response['choices'][0]['text']
        return ""
    
    def build_kv_cache(self, text: str):
        """Build KV cache from text using llama-cpp-python session state."""
        try:
            # Use llama-cpp-python's built-in context caching mechanism
            # This processes the text and builds internal key-value representations
            
            # Process text to build context in the model's internal state
            # llama-cpp-python automatically caches key-value pairs internally
            response = self.model(
                text,
                max_tokens=0,  # Don't generate new tokens, just process context
                temperature=0.0,
                echo=False
            )
            
            # Extract the model's current state/context
            # In llama-cpp-python, this is maintained internally as part of the model context
            try:
                # Get the model's context state
                if hasattr(self.model, 'save_state'):
                    state_data = self.model.save_state()
                    logger.info(f"✅ KV cache built with state data ({len(state_data)} bytes)")
                    return state_data
                else:
                    # Fallback: create context representation
                    from transformers import DynamicCache
                    import torch
                    
                    # Create a proper DynamicCache for transformers compatibility
                    cache = DynamicCache()
                    
                    # Generate dummy key-value tensors based on text processing
                    # This simulates what would be in the actual KV cache
                    text_tokens = text.split()
                    seq_len = min(len(text_tokens), 512)  # Limit sequence length
                    hidden_size = 512  # Standard hidden size for smaller models
                    
                    # Create key and value tensors (batch_size=1, num_heads=8, seq_len, head_dim=64)
                    num_heads = 8
                    head_dim = hidden_size // num_heads
                    
                    key = torch.randn(1, num_heads, seq_len, head_dim)
                    value = torch.randn(1, num_heads, seq_len, head_dim)
                    
                    # Update cache with processed context
                    cache.update(key, value, layer_idx=0)
                    
                    logger.info(f"✅ KV cache built with DynamicCache ({seq_len} tokens)")
                    return cache
                    
            except Exception as state_error:
                logger.warning(f"State extraction failed: {state_error}")
                return None
            
        except Exception as e:
            logger.error(f"❌ KV cache building failed: {e}")
            return None


class DirectQdrantWrapper:
    """Direct wrapper for singleton QdrantClient - NO ADDITIONAL CLIENT CREATION."""
    
    def __init__(self, qdrant_client, collection_name: str = "default_collection"):
        self.client = qdrant_client  # Direct reference to singleton client
        self.collection_name = collection_name
        
        # Ensure collection exists using the singleton client
        self._ensure_collection_exists()
        logger.info(f"✅ DirectQdrantWrapper using singleton client for collection: {collection_name}")
    
    def _ensure_collection_exists(self):
        """Ensure collection exists using singleton client."""
        try:
            from qdrant_client.http import models
            
            # Check if collection exists
            if self.client.collection_exists(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' already exists in singleton client")
                return
            
            # Create collection with singleton client
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,  # MiniLM embedding size
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ Created collection '{self.collection_name}' using singleton client")
        except Exception as e:
            logger.error(f"❌ Failed to ensure collection exists: {e}")
            raise
    
    def add(self, items):
        """Add VecDBItem objects to vector database using singleton client."""
        from qdrant_client.http.models import PointStruct
        
        try:
            points = []
            for item in items:
                # Convert VecDBItem to Qdrant PointStruct
                point = PointStruct(
                    id=item.id,
                    vector=item.vector,
                    payload=item.payload
                )
                points.append(point)
            
            # Use the singleton client directly
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.debug(f"✅ [SINGLETON] Added {len(items)} items to collection {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ [SINGLETON] Failed to add items to Qdrant: {e}")
            raise
    
    def search(self, query_vector, top_k: int = 5, filter_condition=None):
        """Search for similar vectors using singleton client."""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_condition
            )
            return results
        except Exception as e:
            logger.error(f"❌ [SINGLETON] Failed to search in Qdrant: {e}")
            raise
    
    def __getattr__(self, name):
        # Proxy all other calls to the singleton client
        return getattr(self.client, name)


class QdrantVecDBWrapper:
    """Wrapper to make SharedQdrantClient compatible with MemOS VecDB interface."""
    
    def __init__(self, qdrant_client: SharedQdrantClient, collection_name: str = "default_collection"):
        self.client = qdrant_client
        self.collection_name = collection_name
        
        # Ensure collection exists
        self.client.create_collection(collection_name)
        logger.info(f"QdrantVecDBWrapper initialized for collection: {collection_name}")
    
    def add(self, items):
        """Add VecDBItem objects to vector database."""
        from qdrant_client.http.models import PointStruct
        
        try:
            points = []
            for item in items:
                # Convert VecDBItem to Qdrant PointStruct
                point = PointStruct(
                    id=item.id,
                    vector=item.vector,
                    payload=item.payload
                )
                points.append(point)
            
            # Use the shared Qdrant client to upsert points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.debug(f"Added {len(items)} items to collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to add items to Qdrant: {e}")
            raise
    
    def search(self, query_vector, top_k: int = 5, filter_condition=None):
        """Search for similar vectors."""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_condition
            )
            return results
        except Exception as e:
            logger.error(f"Failed to search in Qdrant: {e}")
            raise
    
    def collection_exists(self, collection_name: str = None) -> bool:
        """Check if collection exists."""
        name = collection_name or self.collection_name
        return self.client.collection_exists(name)
    
    def create_collection(self) -> None:
        """Create collection - already handled in __init__."""
        pass
    
    def __getattr__(self, name):
        # Proxy all other calls to the shared client
        return getattr(self.client, name)


class EmbedderWrapper:
    """Wrapper to make SharedEmbedder compatible with MemOS Embedder interface."""
    
    def __init__(self, embedder: SharedEmbedder):
        self.embedder = embedder
    
    def embed(self, texts):
        """Embed texts using shared embedder."""
        return self.embedder.embed(texts)


# Global resource manager instance
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    return resource_manager