"""
Markdown Preference Parser

This module provides functionality to parse user preferences from Markdown files
and convert them to the format expected by the existing GenericKVMemory system.

Author: Claude Code Assistant
Date: 2025-08-02
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MarkdownPreferenceParser:
    """
    Parses user preferences from Markdown format and converts them to
    the existing GenericKVMemory format for backward compatibility.
    """
    
    def __init__(self, markdown_file_path: str):
        """
        Initialize the parser with a path to the markdown preferences file.
        
        Args:
            markdown_file_path: Path to the user_preferences.md file
        """
        self.markdown_file_path = markdown_file_path
        self.preferences = {}
        
    def parse_preferences(self) -> Dict[str, Any]:
        """
        Parse the Markdown file and return preferences in GenericKVMemory format.
        
        Returns:
            Dictionary of preferences in the format:
            {
                "category.key": {
                    "value": "preference_value",
                    "updated_at": "2025-08-02T10:30:00",
                    "description": "Optional description"
                }
            }
        """
        if not os.path.exists(self.markdown_file_path):
            logger.warning(f"Preferences file not found: {self.markdown_file_path}")
            return {}
        
        try:
            with open(self.markdown_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            preferences = self._parse_markdown_content(content)
            logger.info(f"✅ Parsed {len(preferences)} preferences from {self.markdown_file_path}")
            return preferences
            
        except Exception as e:
            logger.error(f"❌ Failed to parse preferences file: {e}")
            return {}
    
    def _parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """
        Parse the markdown content and extract preferences.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Dictionary of parsed preferences
        """
        preferences = {}
        current_category = None
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and main title
            if not line or line.startswith('# User AI Preferences'):
                i += 1
                continue
            
            # Category headers (## Category Name)
            if line.startswith('## '):
                current_category = self._normalize_category_name(line[3:].strip())
                i += 1
                continue
            
            # Preference entries (### Preference Name)
            if line.startswith('### ') and current_category:
                preference_name = self._normalize_preference_name(line[4:].strip())
                preference_key = f"{current_category}.{preference_name}"
                
                # Parse the preference block
                preference_data, lines_consumed = self._parse_preference_block(lines, i + 1)
                
                if preference_data:
                    preferences[preference_key] = preference_data
                
                i += lines_consumed + 1
                continue
            
            i += 1
        
        return preferences
    
    def _parse_preference_block(self, lines: List[str], start_index: int) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Parse a single preference block starting from the given line index.
        
        Args:
            lines: All lines from the markdown file
            start_index: Index to start parsing from
            
        Returns:
            Tuple of (preference_data, lines_consumed)
        """
        value = None
        description = None
        lines_consumed = 0
        
        i = start_index
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop at next preference or category
            if line.startswith('###') or line.startswith('##'):
                break
            
            # Parse value line
            value_match = re.match(r'^-\s*\*\*Value\*\*:\s*`(.+)`', line)
            if value_match:
                value = value_match.group(1)
                lines_consumed = i - start_index + 1
                i += 1
                continue
            
            # Parse description line
            desc_match = re.match(r'^-\s*\*\*Description\*\*:\s*(.+)', line)
            if desc_match:
                description = desc_match.group(1)
                lines_consumed = i - start_index + 1
                i += 1
                continue
            
            # Skip empty lines within the block
            if not line:
                i += 1
                continue
            
            # If we hit content that doesn't match our pattern, stop
            if line and not line.startswith('-'):
                break
                
            i += 1
        
        if value is not None:
            return {
                "value": self._convert_value_type(value),
                "updated_at": datetime.now().isoformat(),
                "description": description
            }, lines_consumed
        
        return None, lines_consumed
    
    def _normalize_category_name(self, category: str) -> str:
        """
        Normalize category name to match existing system conventions.
        
        Args:
            category: Raw category name from markdown
            
        Returns:
            Normalized category name
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = re.sub(r'[^a-zA-Z0-9]+', '_', category.lower())
        normalized = re.sub(r'_+', '_', normalized)  # Remove multiple underscores
        normalized = normalized.strip('_')  # Remove leading/trailing underscores
        
        return normalized
    
    def _normalize_preference_name(self, preference: str) -> str:
        """
        Normalize preference name to match existing system conventions.
        
        Args:
            preference: Raw preference name from markdown
            
        Returns:
            Normalized preference name
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = re.sub(r'[^a-zA-Z0-9]+', '_', preference.lower())
        normalized = re.sub(r'_+', '_', normalized)  # Remove multiple underscores
        normalized = normalized.strip('_')  # Remove leading/trailing underscores
        
        return normalized
    
    def _convert_value_type(self, value: str) -> Any:
        """
        Convert string value to appropriate Python type.
        
        Args:
            value: String value from markdown
            
        Returns:
            Converted value (str, int, float, bool, or list)
        """
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle null values
        if value.lower() in ('null', 'none', ''):
            return None
        
        # Handle arrays (simple JSON-like format)
        if value.startswith('[') and value.endswith(']'):
            try:
                # Simple list parsing for strings
                content = value[1:-1].strip()
                if not content:
                    return []
                
                # Split by comma and clean up quotes
                items = [item.strip().strip('"\'') for item in content.split(',')]
                return items
            except Exception:
                pass
        
        # Try to convert to number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def write_preferences_to_json(self, output_path: str, preferences: Optional[Dict[str, Any]] = None) -> bool:
        """
        Write preferences to JSON format for compatibility with GenericKVMemory.
        
        Args:
            output_path: Path to write the JSON file
            preferences: Preferences dict (will parse from markdown if None)
            
        Returns:
            True if successful, False otherwise
        """
        import json
        
        if preferences is None:
            preferences = self.parse_preferences()
        
        try:
            # Ensure directory exists (only if output_path contains a directory)
            dir_path = os.path.dirname(output_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Wrote {len(preferences)} preferences to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write preferences to JSON: {e}")
            return False
    
    def get_preference_by_key(self, key: str, preferences: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get a specific preference value by key.
        
        Args:
            key: Preference key (e.g., "coding_style.indentation")
            preferences: Preferences dict (will parse from markdown if None)
            
        Returns:
            The preference value, or None if not found
        """
        if preferences is None:
            preferences = self.parse_preferences()
        
        preference_entry = preferences.get(key)
        if preference_entry and isinstance(preference_entry, dict):
            return preference_entry.get("value")
        
        return preference_entry  # For backward compatibility
    
    def validate_markdown_format(self) -> Tuple[bool, List[str]]:
        """
        Validate the markdown file format and return any issues found.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if not os.path.exists(self.markdown_file_path):
            return False, [f"File not found: {self.markdown_file_path}"]
        
        try:
            with open(self.markdown_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, [f"Could not read file: {e}"]
        
        lines = content.split('\n')
        
        # Check for main title
        has_main_title = any(line.strip().startswith('# ') for line in lines)
        if not has_main_title:
            issues.append("Missing main title (# User AI Preferences)")
        
        # Check for at least one category
        has_category = any(line.strip().startswith('## ') for line in lines)
        if not has_category:
            issues.append("No categories found (## Category Name)")
        
        # Check for preference format
        preference_blocks = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('### '):
                preference_blocks += 1
                # Check if the next few lines contain Value pattern
                has_value = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r'^-\s*\*\*Value\*\*:', lines[j].strip()):
                        has_value = True
                        break
                
                if not has_value:
                    issues.append(f"Preference '{line.strip()}' missing **Value** field")
        
        if preference_blocks == 0:
            issues.append("No preferences found (### Preference Name)")
        
        is_valid = len(issues) == 0
        return is_valid, issues


def create_sample_preferences_file(file_path: str) -> bool:
    """
    Create a sample user_preferences.md file with common preferences.
    
    Args:
        file_path: Path where to create the sample file
        
    Returns:
        True if successful, False otherwise
    """
    sample_content = '''# User AI Preferences

## Coding Style

### Indentation
- **Value**: `4 spaces`
- **Description**: Use 4 spaces for indentation instead of tabs

### Naming Convention
- **Value**: `snake_case`
- **Description**: Use snake_case for variable and function names

### Comment Style
- **Value**: `detailed`
- **Description**: Always provide detailed comments in code

## Language & Framework Rules

### Primary Language
- **Value**: `Python`
- **Description**: Write code only in Python unless explicitly requested otherwise

### Web Framework
- **Value**: `FastAPI`
- **Description**: For web development, use the FastAPI framework

### Testing Framework
- **Value**: `pytest`
- **Description**: Use pytest for writing unit tests

## Architecture Preferences

### Code Organization
- **Value**: `modular`
- **Description**: Organize code in small, focused modules with clear responsibilities

### Error Handling
- **Value**: `explicit`
- **Description**: Use explicit try-catch blocks and meaningful error messages

## Libraries & Dependencies

### HTTP Client
- **Value**: `httpx`
- **Description**: Prefer httpx over requests for HTTP operations

### JSON Handling
- **Value**: `pydantic`
- **Description**: Use Pydantic models for JSON validation and serialization

## Project-Specific Preferences

### Documentation Level
- **Value**: `comprehensive`
- **Description**: Generate comprehensive docstrings and inline documentation

### Code Review Focus
- **Value**: `security_first`
- **Description**: Prioritize security considerations in all code reviews

## General Instructions

### AI Persona
- **Value**: `senior_engineer`
- **Description**: Act as a senior software engineer with 10+ years experience

### Response Style
- **Value**: `concise_technical`
- **Description**: Provide concise, technically accurate responses with examples
'''
    
    try:
        # Ensure directory exists (only if file_path contains a directory)
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        logger.info(f"✅ Created sample preferences file: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create sample preferences file: {e}")
        return False


# Convenience functions for direct usage
def parse_preferences_from_markdown(markdown_file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse preferences from a markdown file.
    
    Args:
        markdown_file_path: Path to the user_preferences.md file
        
    Returns:
        Dictionary of preferences in GenericKVMemory format
    """
    parser = MarkdownPreferenceParser(markdown_file_path)
    return parser.parse_preferences()


def convert_markdown_to_json(markdown_file_path: str, json_file_path: str) -> bool:
    """
    Convenience function to convert markdown preferences to JSON format.
    
    Args:
        markdown_file_path: Path to the user_preferences.md file
        json_file_path: Path where to write the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    parser = MarkdownPreferenceParser(markdown_file_path)
    preferences = parser.parse_preferences()
    return parser.write_preferences_to_json(json_file_path, preferences)