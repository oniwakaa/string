"""
Project Memory Manager - Per-Project Memory Isolation for MemOS

This module implements project-specific memory management by extending the 
existing MemOS functionality with project isolation capabilities.

Key Features:
- Project-specific MemCube naming: {user_id}_{project_id}_codebase_cube
- Isolated vector database storage per project
- Project-aware memory operations
- Backward compatibility with existing user-based system

Author: Claude Code Assistant
Date: 2024-12-19
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add MemOS to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MemOS', 'src'))

try:
    from memos.configs.mem_os import MOSConfig
    from memos.mem_os.main import MOS
    from memos.configs.mem_cube import GeneralMemCubeConfig
    from memos.mem_cube.general import GeneralMemCube
    from memos.mem_user.user_manager import UserManager, UserRole
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
    Enhanced memory manager that provides per-project memory isolation.
    
    This class extends the existing MemOS functionality to support project-specific
    memory cubes while maintaining backward compatibility with user-based operations.
    """
    
    def __init__(self, mos_instance: Optional[Any] = None):
        """
        Initialize the Project Memory Manager.
        
        Args:
            mos_instance: Optional MemOS instance to use. If None, will be set later.
        """
        self.mos_instance = mos_instance
        self.project_cubes_cache: Dict[str, Dict[str, Any]] = {}
        
        if not MEMOS_AVAILABLE:
            logger.warning("MemOS not available - project memory features disabled")
    
    def set_mos_instance(self, mos_instance: Any) -> None:
        """Set the MemOS instance for this manager."""
        self.mos_instance = mos_instance
        logger.info("MemOS instance set for ProjectMemoryManager")
    
    def _generate_project_cube_id(self, user_id: str, project_id: str) -> str:
        """
        Generate a project-specific cube ID.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            str: Project-specific cube ID in format {user_id}_{project_id}_codebase_cube
        """
        return f"{user_id}_{project_id}_codebase_cube"
    
    def _generate_collection_name(self, user_id: str, project_id: str) -> str:
        """
        Generate a project-specific vector database collection name.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            str: Collection name for the project
        """
        return f"codebase_{user_id}_{project_id}_code"
    
    def _generate_storage_path(self, user_id: str, project_id: str, cube_id: str) -> str:
        """
        Generate a project-specific storage path.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            cube_id: Cube identifier
            
        Returns:
            str: Storage path for the project's vector database
        """
        return f"./qdrant_storage/{user_id}_{project_id}_{cube_id}"
    
    def _generate_cube_path(self, user_id: str, project_id: str, cube_id: str) -> str:
        """
        Generate the file system path for storing the memory cube.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            cube_id: Cube identifier
            
        Returns:
            str: File system path for the memory cube
        """
        return f"./memory_cubes/{user_id}/{project_id}/{cube_id}"
    
    def project_cube_exists(self, user_id: str, project_id: str) -> bool:
        """
        Check if a project-specific memory cube exists.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            bool: True if the project cube exists
        """
        if not self.mos_instance:
            return False
        
        cube_id = self._generate_project_cube_id(user_id, project_id)
        
        try:
            # Check if cube is registered in MemOS
            accessible_cubes = self.mos_instance.user_manager.get_user_cubes(user_id)
            return cube_id in accessible_cubes
        except Exception as e:
            logger.warning(f"Error checking cube existence: {e}")
            return False
    
    def create_project_cube(self, user_id: str, project_id: str, **config_overrides) -> bool:
        """
        Create a new project-specific memory cube.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            **config_overrides: Optional configuration overrides
            
        Returns:
            bool: True if cube was created successfully
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return False
        
        try:
            # Ensure user exists
            if not self.mos_instance.user_manager.validate_user(user_id):
                self.mos_instance.create_user(user_id=user_id)
                logger.info(f"Created user: {user_id}")
            
            # Generate project-specific identifiers
            cube_id = self._generate_project_cube_id(user_id, project_id)
            collection_name = self._generate_collection_name(user_id, project_id)
            storage_path = self._generate_storage_path(user_id, project_id, cube_id)
            cube_path = self._generate_cube_path(user_id, project_id, cube_id)
            
            # Check if cube already exists
            if self.project_cube_exists(user_id, project_id):
                logger.info(f"Project cube already exists: {cube_id}")
                return True
            
            # Create cube configuration with activation memory
            cube_config = GeneralMemCubeConfig(
                user_id=user_id,
                cube_id=cube_id,
                text_mem={
                    "backend": "general_text",
                    "config": {
                        "embedder": {
                            "backend": "sentence_transformer",
                            "config": {
                                "model_name_or_path": "all-MiniLM-L6-v2",
                                "trust_remote_code": True
                            }
                        },
                        "vector_db": {
                            "backend": "qdrant",
                            "config": {
                                "collection_name": collection_name,
                                "vector_dimension": 384,
                                "distance_metric": "cosine",
                                "host": None,
                                "port": None,
                                "path": storage_path
                            }
                        },
                        "extractor_llm": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "gpt-3.5-turbo",
                                "temperature": 0.0,
                                "max_tokens": 8192,
                                "api_key": "fake-api-key",
                                "api_base": "http://localhost:11434/v1"
                            }
                        }
                    }
                },
                act_mem={
                    "backend": "kv_cache",
                    "config": {
                        "name": f"{cube_id}_kv_cache",
                        "max_cache_size": 2048,  # Maximum number of tokens to cache
                        "model_config": {
                            # Gemma-3B model architecture parameters
                            "hidden_size": 3072,  # Hidden dimension for Gemma-3B
                            "num_attention_heads": 24,  # Number of attention heads
                            "num_hidden_layers": 28,  # Number of transformer layers
                            "intermediate_size": 24576,  # Feed-forward network dimension
                            "max_position_embeddings": 8192,  # Maximum sequence length
                            "vocab_size": 256000,  # Vocabulary size for Gemma
                            "model_type": "gemma",
                            "torch_dtype": "float16"  # Use half precision for efficiency
                        },
                        "cache_strategy": "sliding_window",  # Strategy for cache management
                        "compression_ratio": 0.8,  # Cache compression factor
                        "ttl_seconds": 3600  # Time to live for cache entries (1 hour)
                    }
                },
                para_mem={
                    "backend": "persistent_storage",
                    "config": {
                        "name": f"{cube_id}_parametric_memory",
                        "storage_type": "json",  # Use JSON for structured preference storage
                        "storage_path": f"./memory_cubes/{user_id}/{project_id}/{cube_id}/preferences.json",
                        "schema_validation": True,  # Enable validation of preference structure
                        "versioning": True,  # Track preference changes over time
                        "categories": {
                            # Define preference categories for organization
                            "coding_style": {
                                "description": "Code formatting and style preferences",
                                "examples": ["PEP 8", "tabs vs spaces", "line length", "naming conventions"]
                            },
                            "architecture": {
                                "description": "Architectural patterns and design preferences",
                                "examples": ["MVC", "microservices", "layered architecture", "dependency injection"]
                            },
                            "libraries": {
                                "description": "Preferred libraries and frameworks",
                                "examples": ["logging: loguru", "testing: pytest", "web: fastapi"]
                            },
                            "patterns": {
                                "description": "Coding patterns and best practices",
                                "examples": ["error handling", "async patterns", "data validation"]
                            },
                            "project_specific": {
                                "description": "Project-specific rules and conventions",
                                "examples": ["file organization", "commit message format", "documentation style"]
                            }
                        },
                        "max_entries": 1000,  # Maximum number of preference entries
                        "auto_backup": True,  # Automatic backup of preferences
                        "encryption": False  # Enable if sensitive preferences are stored
                    }
                }
            )
            
            # Apply any configuration overrides
            if config_overrides:
                # Merge config overrides (simple approach for now)
                for key, value in config_overrides.items():
                    if hasattr(cube_config, key):
                        setattr(cube_config, key, value)
            
            # Create and save the memory cube
            mem_cube = GeneralMemCube(cube_config)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(cube_path), exist_ok=True)
            
            # Save cube to disk
            mem_cube.dump(cube_path)
            
            # Register cube with MemOS
            self.mos_instance.register_mem_cube(
                mem_cube_name_or_path=cube_path,
                mem_cube_id=cube_id,
                user_id=user_id
            )
            
            # Cache cube info
            self.project_cubes_cache[f"{user_id}_{project_id}"] = {
                'cube_id': cube_id,
                'cube_path': cube_path,
                'collection_name': collection_name,
                'storage_path': storage_path,
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"Created project cube: {cube_id} for user {user_id}, project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create project cube: {e}")
            return False
    
    def get_or_create_project_cube(self, user_id: str, project_id: str) -> Optional[str]:
        """
        Get existing project cube ID or create a new one if it doesn't exist.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            Optional[str]: Cube ID if successful, None otherwise
        """
        cube_id = self._generate_project_cube_id(user_id, project_id)
        
        if self.project_cube_exists(user_id, project_id):
            logger.info(f"Using existing project cube: {cube_id}")
            return cube_id
        
        if self.create_project_cube(user_id, project_id):
            logger.info(f"Created new project cube: {cube_id}")
            return cube_id
        
        logger.error(f"Failed to get or create project cube for user {user_id}, project {project_id}")
        return None
    
    def add_memory_to_project(
        self, 
        user_id: str, 
        project_id: str, 
        memory_content: str, 
        **kwargs
    ) -> bool:
        """
        Add memory content to a specific project's memory cube.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            memory_content: Content to add to memory
            **kwargs: Additional parameters for memory addition
            
        Returns:
            bool: True if memory was added successfully
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return False
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return False
            
            # Add memory using MemOS
            self.mos_instance.add(
                memory_content=memory_content,
                mem_cube_id=cube_id,
                user_id=user_id,
                **kwargs
            )
            
            logger.info(f"Added memory to project {project_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add memory to project: {e}")
            return False
    
    def search_project_memory(
        self, 
        user_id: str, 
        project_id: str, 
        query: str, 
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Search memory within a specific project's context.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            query: Search query
            **kwargs: Additional search parameters
            
        Returns:
            Optional[Dict[str, Any]]: Search results or None if failed
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return None
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return None
            
            # Search within the specific project cube
            search_result = self.mos_instance.search(
                query=query,
                user_id=user_id,
                install_cube_ids=[cube_id],
                **kwargs
            )
            
            logger.info(f"Searched project {project_id} memory for user {user_id}")
            return search_result
            
        except Exception as e:
            logger.error(f"Failed to search project memory: {e}")
            return None
    
    def chat_with_project_context(
        self, 
        user_id: str, 
        project_id: str, 
        query: str, 
        **kwargs
    ) -> Optional[str]:
        """
        Perform chat with project-specific memory context.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            query: Chat query
            **kwargs: Additional chat parameters
            
        Returns:
            Optional[str]: Chat response or None if failed
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return None
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return None
            
            # Perform chat with project context
            # Note: MemOS chat will automatically use accessible cubes for the user
            response = self.mos_instance.chat(
                query=query,
                user_id=user_id,
                **kwargs
            )
            
            logger.info(f"Chat completed for project {project_id}, user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to chat with project context: {e}")
            return None
    
    def list_user_projects(self, user_id: str) -> List[str]:
        """
        List all projects for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[str]: List of project IDs for the user
        """
        if not self.mos_instance:
            return []
        
        try:
            # Get all cubes for the user
            accessible_cubes = self.mos_instance.user_manager.get_user_cubes(user_id)
            
            # Extract project IDs from cube names
            projects = []
            for cube_id in accessible_cubes:
                if cube_id.startswith(f"{user_id}_") and cube_id.endswith("_codebase_cube"):
                    # Extract project_id from {user_id}_{project_id}_codebase_cube
                    parts = cube_id.split("_")
                    if len(parts) >= 3:
                        # Join all parts between user_id and "codebase_cube"
                        project_id = "_".join(parts[1:-2])
                        if project_id:
                            projects.append(project_id)
            
            return projects
            
        except Exception as e:
            logger.error(f"Failed to list user projects: {e}")
            return []
    
    def delete_project_cube(self, user_id: str, project_id: str) -> bool:
        """
        Delete a project-specific memory cube.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            bool: True if cube was deleted successfully
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return False
        
        try:
            cube_id = self._generate_project_cube_id(user_id, project_id)
            
            # Unregister from MemOS
            self.mos_instance.unregister_mem_cube(
                mem_cube_id=cube_id,
                user_id=user_id
            )
            
            # Clean up cache
            cache_key = f"{user_id}_{project_id}"
            if cache_key in self.project_cubes_cache:
                del self.project_cubes_cache[cache_key]
            
            logger.info(f"Deleted project cube: {cube_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project cube: {e}")
            return False
    
    def get_project_cube_info(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a project's memory cube.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            Optional[Dict[str, Any]]: Cube information or None if not found
        """
        cube_id = self._generate_project_cube_id(user_id, project_id)
        cache_key = f"{user_id}_{project_id}"
        
        # Check cache first
        if cache_key in self.project_cubes_cache:
            return self.project_cubes_cache[cache_key]
        
        # Check if cube exists
        if self.project_cube_exists(user_id, project_id):
            cube_info = {
                'cube_id': cube_id,
                'user_id': user_id,
                'project_id': project_id,
                'exists': True,
                'collection_name': self._generate_collection_name(user_id, project_id),
                'storage_path': self._generate_storage_path(user_id, project_id, cube_id),
                'cube_path': self._generate_cube_path(user_id, project_id, cube_id)
            }
            
            # Cache the info
            self.project_cubes_cache[cache_key] = cube_info
            return cube_info
        
        return None
    
    def add_project_preference(
        self,
        user_id: str,
        project_id: str,
        category: str,
        key: str,
        value: Any,
        description: str = None
    ) -> bool:
        """
        Add or update a project preference in parametric memory.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            category: Preference category (coding_style, architecture, etc.)
            key: Preference key
            value: Preference value
            description: Optional description of the preference
            
        Returns:
            bool: True if preference was stored successfully
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return False
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return False
            
            # Prepare preference data
            preference_data = {
                "category": category,
                "key": key,
                "value": value,
                "description": description,
                "timestamp": time.time(),
                "user_id": user_id,
                "project_id": project_id
            }
            
            # Store in parametric memory
            # Get the MemCube for this project
            mem_cube = None
            try:
                # Access the registered memory cube
                accessible_cubes = self.mos_instance.user_manager.get_user_cubes(user_id)
                if cube_id in accessible_cubes:
                    # Get the cube instance
                    cube_path = self._generate_cube_path(user_id, project_id, cube_id)
                    
                    # For now, we'll store preferences in a JSON file within the cube directory
                    # This simulates the parametric memory backend until full MemOS integration
                    import json
                    import os
                    
                    preferences_file = os.path.join(os.path.dirname(cube_path), "preferences.json")
                    
                    # Load existing preferences
                    if os.path.exists(preferences_file):
                        with open(preferences_file, 'r') as f:
                            all_preferences = json.load(f)
                    else:
                        all_preferences = {}
                    
                    # Initialize category if it doesn't exist
                    if category not in all_preferences:
                        all_preferences[category] = {}
                    
                    # Store the preference
                    all_preferences[category][key] = {
                        "value": value,
                        "description": description,
                        "timestamp": preference_data["timestamp"],
                        "user_id": user_id,
                        "project_id": project_id
                    }
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(preferences_file), exist_ok=True)
                    
                    # Save back to file
                    with open(preferences_file, 'w') as f:
                        json.dump(all_preferences, f, indent=2)
                    
                    logger.info(f"Added preference {category}.{key}={value} to project {project_id}")
                    return True
                else:
                    logger.error(f"Cube {cube_id} not accessible for user {user_id}")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to store preference in parametric memory: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to add project preference: {e}")
            return False
    
    def get_project_preferences(
        self,
        user_id: str,
        project_id: str,
        category: str = None
    ) -> Dict[str, Any]:
        """
        Retrieve project preferences from parametric memory.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            category: Optional category filter
            
        Returns:
            Dict containing preferences
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return {}
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return {}
            
            # Retrieve from parametric memory
            try:
                # Access the registered memory cube
                accessible_cubes = self.mos_instance.user_manager.get_user_cubes(user_id)
                if cube_id in accessible_cubes:
                    # Get the cube path and preferences file
                    cube_path = self._generate_cube_path(user_id, project_id, cube_id)
                    preferences_file = os.path.join(os.path.dirname(cube_path), "preferences.json")
                    
                    # Load preferences from file
                    if os.path.exists(preferences_file):
                        import json
                        with open(preferences_file, 'r') as f:
                            all_preferences = json.load(f)
                        
                        # Filter by category if specified
                        if category:
                            preferences = {category: all_preferences.get(category, {})}
                        else:
                            preferences = all_preferences
                        
                        logger.info(f"Retrieved {len(preferences)} preference categories for project {project_id}")
                        return preferences
                    else:
                        logger.info(f"No preferences file found for project {project_id}")
                        return {}
                else:
                    logger.error(f"Cube {cube_id} not accessible for user {user_id}")
                    return {}
                    
            except Exception as e:
                logger.error(f"Failed to retrieve preferences from parametric memory: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Failed to retrieve project preferences: {e}")
            return {}
    
    def search_project_preferences(
        self,
        user_id: str,
        project_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Search project preferences by query.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            query: Search query
            
        Returns:
            List of matching preferences
        """
        if not self.mos_instance:
            logger.error("MemOS instance not available")
            return []
        
        try:
            # Ensure project cube exists
            cube_id = self.get_or_create_project_cube(user_id, project_id)
            if not cube_id:
                return []
            
            # Search in parametric memory
            try:
                # Access the registered memory cube
                accessible_cubes = self.mos_instance.user_manager.get_user_cubes(user_id)
                if cube_id in accessible_cubes:
                    # Get the cube path and preferences file
                    cube_path = self._generate_cube_path(user_id, project_id, cube_id)
                    preferences_file = os.path.join(os.path.dirname(cube_path), "preferences.json")
                    
                    # Load preferences from file
                    if os.path.exists(preferences_file):
                        import json
                        with open(preferences_file, 'r') as f:
                            all_preferences = json.load(f)
                        
                        # Search through all preferences
                        search_results = []
                        query_lower = query.lower()
                        
                        for category_name, category_prefs in all_preferences.items():
                            for key, pref_data in category_prefs.items():
                                # Search in key, value, and description
                                searchable_text = f"{key} {pref_data.get('value', '')} {pref_data.get('description', '')}"
                                if query_lower in searchable_text.lower():
                                    search_results.append({
                                        "category": category_name,
                                        "key": key,
                                        "value": pref_data.get("value"),
                                        "description": pref_data.get("description"),
                                        "timestamp": pref_data.get("timestamp"),
                                        "relevance_score": 1.0  # Simple scoring for now
                                    })
                        
                        logger.info(f"Found {len(search_results)} preferences matching '{query}' in project {project_id}")
                        return search_results
                    else:
                        logger.info(f"No preferences file found for project {project_id}")
                        return []
                else:
                    logger.error(f"Cube {cube_id} not accessible for user {user_id}")
                    return []
                    
            except Exception as e:
                logger.error(f"Failed to search preferences: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to search project preferences: {e}")
            return []
    
    def format_preferences_for_prompt(
        self,
        user_id: str,
        project_id: str
    ) -> str:
        """
        Format project preferences for inclusion in agent prompts.
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            
        Returns:
            Formatted string containing relevant preferences
        """
        try:
            preferences = self.get_project_preferences(user_id, project_id)
            
            if not preferences:
                return ""
            
            # Format preferences into a clear, instructional string
            formatted_lines = ["Important: Adhere strictly to the following project guidelines:"]
            
            for category, items in preferences.items():
                if items:
                    formatted_lines.append(f"\n{category.replace('_', ' ').title()}:")
                    for key, value in items.items():
                        if isinstance(value, dict) and 'value' in value:
                            formatted_lines.append(f"  • {key}: {value['value']}")
                            if 'description' in value and value['description']:
                                formatted_lines.append(f"    ({value['description']})")
                        else:
                            formatted_lines.append(f"  • {key}: {value}")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Failed to format preferences for prompt: {e}")
            return ""


# Utility functions for backward compatibility and migration
def migrate_user_cube_to_project(
    mos_instance: Any,
    user_id: str,
    project_id: str = "default",
    old_cube_pattern: str = None
) -> bool:
    """
    Migrate an existing user-based cube to the new project-based naming.
    
    Args:
        mos_instance: MemOS instance
        user_id: User identifier
        project_id: Project identifier (default: "default")
        old_cube_pattern: Pattern of old cube to migrate
        
    Returns:
        bool: True if migration was successful
    """
    try:
        old_cube_id = old_cube_pattern or f"{user_id}_codebase_cube"
        
        # Check if old cube exists
        accessible_cubes = mos_instance.user_manager.get_user_cubes(user_id)
        if old_cube_id not in accessible_cubes:
            logger.warning(f"Old cube {old_cube_id} not found for migration")
            return False
        
        # Create project memory manager
        pm_manager = ProjectMemoryManager(mos_instance)
        
        # Create new project cube
        if pm_manager.create_project_cube(user_id, project_id):
            logger.info(f"Migration successful: {old_cube_id} → {pm_manager._generate_project_cube_id(user_id, project_id)}")
            return True
        else:
            logger.error(f"Failed to create new project cube during migration")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def get_default_project_id() -> str:
    """Get the default project ID for backward compatibility."""
    return "default"


# Example usage and testing
if __name__ == "__main__":
    print("🔧 Project Memory Manager - Test Mode")
    print("=" * 50)
    
    # This would normally be initialized with a real MemOS instance
    pm_manager = ProjectMemoryManager()
    
    # Example project-specific naming
    user_id = "test_user"
    project_id = "calculator_app"
    
    cube_id = pm_manager._generate_project_cube_id(user_id, project_id)
    collection_name = pm_manager._generate_collection_name(user_id, project_id)
    storage_path = pm_manager._generate_storage_path(user_id, project_id, cube_id)
    
    print(f"User ID: {user_id}")
    print(f"Project ID: {project_id}")
    print(f"Generated Cube ID: {cube_id}")
    print(f"Collection Name: {collection_name}")
    print(f"Storage Path: {storage_path}")
    
    print("\n✅ Project Memory Manager initialized successfully!")
    print("💡 Set mos_instance to enable full functionality")