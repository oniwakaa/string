"""
GenericKVMemory - Lightweight Parametric Memory Backend

This module provides a simple key-value storage system for project preferences
and configurations, replacing the complex LoRA-based parametric memory system.

It stores preferences as JSON files in project-specific directories, providing
a lightweight alternative for coding style preferences, project settings, etc.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GenericKVMemory:
    """
    Generic Key-Value Memory for Project Preferences.
    
    This class provides a lightweight parametric memory backend that stores
    project-specific preferences and configurations as JSON files, replacing
    the need for LoRA-based model fine-tuning for simple configuration storage.
    """
    
    def __init__(self, storage_path: str):
        """
        Initialize GenericKVMemory with a project-specific storage path.
        
        Args:
            storage_path: Directory path where preferences.json will be stored
        """
        self.storage_path = storage_path
        self.preferences_file = os.path.join(storage_path, "preferences.json")
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        logger.info(f"✅ GenericKVMemory initialized at: {storage_path}")
    
    def add_preference(self, key: str, value: Any, description: str = None) -> bool:
        """
        Add or update a preference in the key-value store.
        
        Args:
            key: Preference key (e.g., "coding_style.indentation")
            value: Preference value (e.g., "4 spaces")
            description: Optional description of the preference
            
        Returns:
            bool: True if preference was saved successfully
        """
        try:
            # Load existing preferences
            preferences = self._load_preferences()
            
            # Update with new preference
            preference_entry = {
                "value": value,
                "updated_at": datetime.now().isoformat(),
                "description": description
            }
            
            preferences[key] = preference_entry
            
            # Save updated preferences
            return self._save_preferences(preferences)
            
        except Exception as e:
            logger.error(f"❌ Failed to add preference '{key}': {e}")
            return False
    
    def get_preference(self, key: str) -> Optional[Any]:
        """
        Get a specific preference by key.
        
        Args:
            key: Preference key to retrieve
            
        Returns:
            The preference value, or None if not found
        """
        try:
            preferences = self._load_preferences()
            preference_entry = preferences.get(key)
            
            if preference_entry and isinstance(preference_entry, dict):
                return preference_entry.get("value")
            
            return preference_entry  # For backward compatibility
            
        except Exception as e:
            logger.error(f"❌ Failed to get preference '{key}': {e}")
            return None
    
    def get_preferences(self) -> Dict[str, Any]:
        """
        Get all preferences as a dictionary.
        
        Returns:
            Dictionary of all stored preferences
        """
        try:
            return self._load_preferences()
        except Exception as e:
            logger.error(f"❌ Failed to load preferences: {e}")
            return {}
    
    def remove_preference(self, key: str) -> bool:
        """
        Remove a preference by key.
        
        Args:
            key: Preference key to remove
            
        Returns:
            bool: True if preference was removed successfully
        """
        try:
            preferences = self._load_preferences()
            
            if key in preferences:
                del preferences[key]
                return self._save_preferences(preferences)
            else:
                logger.warning(f"⚠️ Preference '{key}' not found for removal")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to remove preference '{key}': {e}")
            return False
    
    def clear_preferences(self) -> bool:
        """
        Clear all preferences.
        
        Returns:
            bool: True if preferences were cleared successfully
        """
        try:
            return self._save_preferences({})
        except Exception as e:
            logger.error(f"❌ Failed to clear preferences: {e}")
            return False
    
    def _load_preferences(self) -> Dict[str, Any]:
        """
        Load preferences from JSON file.
        
        Returns:
            Dictionary of preferences, empty dict if file doesn't exist
        """
        if not os.path.exists(self.preferences_file):
            logger.debug(f"Preferences file not found, returning empty dict: {self.preferences_file}")
            return {}
        
        try:
            with open(self.preferences_file, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
                logger.debug(f"✅ Loaded {len(preferences)} preferences from {self.preferences_file}")
                return preferences
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in preferences file: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to load preferences file: {e}")
            return {}
    
    def _save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        Save preferences to JSON file.
        
        Args:
            preferences: Dictionary of preferences to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.preferences_file), exist_ok=True)
            
            # Save with pretty formatting
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"✅ Saved {len(preferences)} preferences to {self.preferences_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save preferences: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the stored preferences.
        
        Returns:
            Dictionary with preference statistics
        """
        preferences = self._load_preferences()
        
        return {
            "total_preferences": len(preferences),
            "storage_path": self.storage_path,
            "file_exists": os.path.exists(self.preferences_file),
            "file_size_bytes": os.path.getsize(self.preferences_file) if os.path.exists(self.preferences_file) else 0,
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(self.preferences_file)
            ).isoformat() if os.path.exists(self.preferences_file) else None
        }
    
    def __str__(self) -> str:
        """String representation of the GenericKVMemory instance."""
        stats = self.get_stats()
        return f"GenericKVMemory(path='{self.storage_path}', preferences={stats['total_preferences']})"