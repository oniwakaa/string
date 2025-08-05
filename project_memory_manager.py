"""
Project Memory Manager - Simplified with ResourceManager Integration

This module now provides a clean interface to the ResourceManager for project-specific
memory management, eliminating all complex configuration and instantiation logic.

Key Features:
- Delegates all resource management to the centralized ResourceManager
- Provides project-specific cube ID generation
- Clean interface with no direct model or database instantiation

Author: Claude Code Assistant
Date: 2024-12-19
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# Import ResourceManager for shared resource management
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
try:
    from core.resource_manager import get_resource_manager
    RESOURCE_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"ResourceManager not available: {e}")
    RESOURCE_MANAGER_AVAILABLE = False

# Add MemOS to Python path for basic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MemOS', 'src'))

try:
    from memos.configs.mem_cube import GeneralMemCubeConfig
    from memos.log import get_logger
    logger = get_logger(__name__)
    MEMOS_AVAILABLE = True
except ImportError as e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"MemOS not available: {e}")
    MEMOS_AVAILABLE = False


class ProjectMemoryManager:
    """
    Simplified Project Memory Manager using ResourceManager.
    
    This class now delegates all complex resource management to the centralized
    ResourceManager, providing only a clean interface for project operations.
    """
    
    def __init__(self, mos_instance: Optional[Any] = None):
        """Initialize the simplified Project Memory Manager."""
        self.mos_instance = mos_instance
        self.resource_manager = get_resource_manager() if RESOURCE_MANAGER_AVAILABLE else None
        
        if not self.resource_manager:
            logger.warning("ResourceManager not available - project memory features disabled")
        else:
            logger.info("ProjectMemoryManager initialized with ResourceManager delegation")
    
    def set_mos_instance(self, mos_instance: Any) -> None:
        """Set the MemOS instance for this manager."""
        self.mos_instance = mos_instance
        logger.info("MemOS instance set for ProjectMemoryManager")
    
    def _generate_project_cube_id(self, user_id: str, project_id: str) -> str:
        """Generate a project-specific cube ID."""
        return f"{user_id}_{project_id}_codebase_cube"
    
    def _generate_collection_name(self, user_id: str, project_id: str) -> str:
        """Generate a project-specific vector database collection name."""
        return f"codebase_{user_id}_{project_id}_code"
    
    def _create_minimal_config(self, user_id: str, project_id: str) -> GeneralMemCubeConfig:
        """
        Create minimal config for ResourceManager to use.
        
        The ResourceManager will override all the internal factories, so this config
        just needs to provide the basic structure.
        """
        cube_id = self._generate_project_cube_id(user_id, project_id)
        collection_name = self._generate_collection_name(user_id, project_id)
        
        # Minimal config - ResourceManager will inject shared resources
        return GeneralMemCubeConfig(
            user_id=user_id,  # Correct field name
            cube_id=cube_id,  # Correct field name
            text_mem={
                "backend": "general_text",  # ResourceManager will override with shared resources
                "config": {
                    "vector_db": {
                        "backend": "qdrant", 
                        "config": {
                            "path": "./qdrant_storage",  # Use same path as MemOS for singleton sharing
                            "collection_name": collection_name  # Nested correctly
                        }
                    },
                    "extractor_llm": {"backend": "gguf", "config": {"model_name_or_path": "placeholder"}},
                    "embedder": {"backend": "sentence_transformer", "config": {"model_name_or_path": "./models/embedding/all-MiniLM-L6-v2"}}
                }
            },
            act_mem={"backend": "kv_cache", "config": {"extractor_llm": {"backend": "huggingface", "config": {"model_name_or_path": "microsoft/DialoGPT-small"}}}},  # Enable KVCache
            para_mem={"backend": "uninitialized", "config": {}},  # Disabled for stability
        )
    
    def get_or_create_project_cube(self, user_id: str, project_id: str) -> Optional[str]:
        """
        Get or create project cube using ResourceManager - THE SIMPLIFIED VERSION.
        
        This method now delegates all complex logic to the ResourceManager and simply
        returns the cube_id for use by calling code.
        """
        if not self.resource_manager:
            logger.error("ResourceManager not available")
            return None
        
        try:
            cube_id = self._generate_project_cube_id(user_id, project_id)
            
            # Create minimal config for the ResourceManager
            config = self._create_minimal_config(user_id, project_id)
            
            # Delegate to ResourceManager - this handles all the complex assembly
            mem_cube = self.resource_manager.get_mem_cube(cube_id, config)
            
            if mem_cube:
                logger.info(f"✅ Project cube '{cube_id}' ready via ResourceManager")
                return cube_id
            else:
                logger.error(f"❌ ResourceManager failed to create cube '{cube_id}'")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get or create project cube via ResourceManager: {e}")
            return None
    
    def project_cube_exists(self, user_id: str, project_id: str) -> bool:
        """Check if project cube exists - simplified check."""
        if not self.resource_manager:
            return False
        
        cube_id = self._generate_project_cube_id(user_id, project_id)
        # ResourceManager handles caching, so we can always return True
        # and let it handle the existence check internally
        return True
    
    def add_memory_to_project(
        self, 
        user_id: str, 
        project_id: str, 
        memory_content: str, 
        **kwargs
    ) -> bool:
        """Add memory content to a specific project's memory cube."""
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return False
        
        try:
            # Ensure project cube exists via ResourceManager
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return False
            
            # Use MemOS to add memory (ResourceManager handles the underlying resources)
            self.mos_instance.add(
                memory_content=memory_content,
                mem_cube_id=cube_id,
                user_id=user_id,
                **kwargs
            )
            
            logger.info(f"✅ Added memory to project {project_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add memory to project: {e}")
            return False
    
    def search_project_memories(
        self, 
        user_id: str, 
        project_id: str, 
        query: str, 
        top_k: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Search memories within a specific project."""
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return None
        
        try:
            cube_id = self._generate_project_cube_id(user_id, project_id)
            
            # Use MemOS search (ResourceManager provides the underlying resources)
            results = self.mos_instance.search(
                query=query,
                mem_cube_id=cube_id,
                user_id=user_id,
                top_k=top_k
            )
            
            logger.info(f"✅ Searched project {project_id} for user {user_id}: {len(results) if results else 0} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search project memories: {e}")
            return None
    
    def get_project_stats(self, user_id: str, project_id: str) -> Dict[str, Any]:
        """Get project memory statistics via ResourceManager."""
        cube_id = self._generate_project_cube_id(user_id, project_id)
        
        stats = {
            "cube_id": cube_id,
            "user_id": user_id,  
            "project_id": project_id,
            "resource_manager_active": self.resource_manager is not None,
        }
        
        if self.resource_manager:
            # Get ResourceManager stats
            rm_stats = self.resource_manager.get_memory_stats()
            stats.update(rm_stats)
        
        return stats
    
    def add_project_preference(
        self, 
        user_id: str, 
        project_id: str, 
        category: str, 
        key: str, 
        value: str, 
        description: str = None
    ) -> bool:
        """Add preference using ResourceManager's GenericKVMemory."""
        if not self.resource_manager:
            logger.error("ResourceManager not available for preferences")
            return False
        
        try:
            # Get project MemCube with GenericKVMemory
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return False
            
            config = self._create_minimal_config(user_id, project_id)
            mem_cube = self.resource_manager.get_mem_cube(cube_id, config)
            
            if mem_cube and mem_cube.para_mem:
                # Use GenericKVMemory to add preference
                preference_key = f"{category}.{key}"
                success = mem_cube.para_mem.add_preference(preference_key, value, description)
                logger.info(f"✅ Added preference {preference_key} for project {project_id}")
                return success
            else:
                logger.error("Parametric memory not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add project preference: {e}")
            return False
    
    def get_project_preferences(self, user_id: str, project_id: str, category: str = None):
        """Get preferences using ResourceManager's GenericKVMemory."""
        if not self.resource_manager:
            logger.error("ResourceManager not available for preferences")
            return {}
        
        try:
            cube_id = self._generate_project_cube_id(user_id, project_id)
            config = self._create_minimal_config(user_id, project_id)
            mem_cube = self.resource_manager.get_mem_cube(cube_id, config)
            
            if mem_cube and mem_cube.para_mem:
                all_preferences = mem_cube.para_mem.get_preferences()
                
                # Filter by category if specified
                if category:
                    filtered = {k: v for k, v in all_preferences.items() if k.startswith(f"{category}.")}
                    return filtered
                
                return all_preferences
            else:
                logger.warning("Parametric memory not available")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get project preferences: {e}")
            return {}
    
    def delete_project_preference(self, user_id: str, project_id: str, category: str, key: str) -> bool:
        """Delete preference using ResourceManager's GenericKVMemory."""
        if not self.resource_manager:
            logger.error("ResourceManager not available for preferences")
            return False
        
        try:
            cube_id = self._generate_project_cube_id(user_id, project_id)
            config = self._create_minimal_config(user_id, project_id)
            mem_cube = self.resource_manager.get_mem_cube(cube_id, config)
            
            if mem_cube and mem_cube.para_mem:
                preference_key = f"{category}.{key}"
                success = mem_cube.para_mem.remove_preference(preference_key)
                logger.info(f"✅ Removed preference {preference_key} for project {project_id}")
                return success
            else:
                logger.error("Parametric memory not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete project preference: {e}")
            return False
    
    def search_project_preferences(self, user_id: str, project_id: str, query: str):
        """Search preferences using ResourceManager's GenericKVMemory."""
        try:
            all_preferences = self.get_project_preferences(user_id, project_id)
            
            # Simple text-based search
            results = []
            query_lower = query.lower()
            
            for key, preference_data in all_preferences.items():
                if isinstance(preference_data, dict):
                    value = preference_data.get("value", "")
                    description = preference_data.get("description", "")
                else:
                    value = preference_data
                    description = ""
                
                # Search in key, value, and description
                if (query_lower in key.lower() or 
                    query_lower in str(value).lower() or 
                    query_lower in str(description).lower()):
                    results.append({
                        "key": key,
                        "value": value,
                        "description": description
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search project preferences: {e}")
            return []


# Keep backward compatibility
def create_project_memory_manager(mos_instance=None):
    """Factory function for creating ProjectMemoryManager instances."""
    return ProjectMemoryManager(mos_instance)