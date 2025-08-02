"""
Unit tests for the Markdown Preference Parser.

Author: Claude Code Assistant
Date: 2025-08-02
"""

import os
import json
import tempfile
import pytest
from datetime import datetime
from unittest.mock import patch

from .preference_parser import (
    MarkdownPreferenceParser,
    parse_preferences_from_markdown,
    convert_markdown_to_json,
    create_sample_preferences_file
)


class TestMarkdownPreferenceParser:
    """Test suite for MarkdownPreferenceParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_markdown_file = os.path.join(self.temp_dir, "test_preferences.md")
        self.test_json_file = os.path.join(self.temp_dir, "test_preferences.json")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_markdown_file(self, content: str):
        """Helper to create a test markdown file."""
        with open(self.test_markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_parse_simple_preferences(self):
        """Test parsing a simple preferences file."""
        content = '''# User AI Preferences

## Coding Style

### Indentation
- **Value**: `4 spaces`
- **Description**: Use 4 spaces for indentation

### Language
- **Value**: `Python`
- **Description**: Primary programming language
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        # Check structure
        assert len(preferences) == 2
        assert "coding_style.indentation" in preferences
        assert "coding_style.language" in preferences
        
        # Check indentation preference
        indent_pref = preferences["coding_style.indentation"]
        assert indent_pref["value"] == "4 spaces"
        assert indent_pref["description"] == "Use 4 spaces for indentation"
        assert "updated_at" in indent_pref
        
        # Check language preference
        lang_pref = preferences["coding_style.language"]
        assert lang_pref["value"] == "Python"
        assert lang_pref["description"] == "Primary programming language"
    
    def test_parse_different_value_types(self):
        """Test parsing different value types (string, int, bool, array)."""
        content = '''# User AI Preferences

## Test Category

### String Value
- **Value**: `hello world`
- **Description**: A string value

### Integer Value
- **Value**: `42`
- **Description**: An integer value

### Float Value
- **Value**: `3.14`
- **Description**: A float value

### Boolean True
- **Value**: `true`
- **Description**: A boolean true value

### Boolean False
- **Value**: `false`
- **Description**: A boolean false value

### Array Value
- **Value**: `["item1", "item2", "item3"]`
- **Description**: An array value

### Null Value
- **Value**: `null`
- **Description**: A null value
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        assert preferences["test_category.string_value"]["value"] == "hello world"
        assert preferences["test_category.integer_value"]["value"] == 42
        assert preferences["test_category.float_value"]["value"] == 3.14
        assert preferences["test_category.boolean_true"]["value"] is True
        assert preferences["test_category.boolean_false"]["value"] is False
        assert preferences["test_category.array_value"]["value"] == ["item1", "item2", "item3"]
        assert preferences["test_category.null_value"]["value"] is None
    
    def test_normalize_category_names(self):
        """Test category name normalization."""
        content = '''# User AI Preferences

## Language & Framework Rules

### Test Preference
- **Value**: `test`
- **Description**: Test

## Project-Specific Preferences

### Another Test
- **Value**: `test2`
- **Description**: Test 2
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        assert "language_framework_rules.test_preference" in preferences
        assert "project_specific_preferences.another_test" in preferences
    
    def test_normalize_preference_names(self):
        """Test preference name normalization."""
        content = '''# User AI Preferences

## Test Category

### Primary Language
- **Value**: `Python`
- **Description**: Test

### HTTP Client Library
- **Value**: `httpx`
- **Description**: Test

### AI-Generated Code Style
- **Value**: `clean`
- **Description**: Test
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        assert "test_category.primary_language" in preferences
        assert "test_category.http_client_library" in preferences
        assert "test_category.ai_generated_code_style" in preferences
    
    def test_missing_description(self):
        """Test handling preferences without descriptions."""
        content = '''# User AI Preferences

## Test Category

### No Description
- **Value**: `test_value`

### With Description
- **Value**: `test_value2`
- **Description**: Has description
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        # Preference without description should still work
        no_desc = preferences["test_category.no_description"]
        assert no_desc["value"] == "test_value"
        assert no_desc["description"] is None
        
        # Preference with description
        with_desc = preferences["test_category.with_description"]
        assert with_desc["value"] == "test_value2"
        assert with_desc["description"] == "Has description"
    
    def test_empty_file(self):
        """Test handling empty or non-existent files."""
        # Test non-existent file
        parser = MarkdownPreferenceParser("non_existent_file.md")
        preferences = parser.parse_preferences()
        assert preferences == {}
        
        # Test empty file
        self.create_test_markdown_file("")
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        assert preferences == {}
    
    def test_malformed_markdown(self):
        """Test handling malformed markdown."""
        content = '''# User AI Preferences

## Test Category

### Incomplete Preference
- **Value**: 

### Missing Value
- **Description**: Only has description

### Good Preference
- **Value**: `working`
- **Description**: This one works
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        # Should only parse the valid preference
        assert len(preferences) == 1
        assert "test_category.good_preference" in preferences
        assert preferences["test_category.good_preference"]["value"] == "working"
    
    def test_get_preference_by_key(self):
        """Test getting specific preferences by key."""
        content = '''# User AI Preferences

## Test Category

### Test Key
- **Value**: `test_value`
- **Description**: Test description
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        
        # Get specific preference
        value = parser.get_preference_by_key("test_category.test_key")
        assert value == "test_value"
        
        # Get non-existent preference
        value = parser.get_preference_by_key("non.existent")
        assert value is None
    
    def test_write_preferences_to_json(self):
        """Test writing preferences to JSON format."""
        content = '''# User AI Preferences

## Test Category

### Test Preference
- **Value**: `json_test`
- **Description**: For JSON testing
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        
        # Write to JSON
        success = parser.write_preferences_to_json(self.test_json_file)
        assert success is True
        assert os.path.exists(self.test_json_file)
        
        # Verify JSON content
        with open(self.test_json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        assert "test_category.test_preference" in json_data
        assert json_data["test_category.test_preference"]["value"] == "json_test"
        assert json_data["test_category.test_preference"]["description"] == "For JSON testing"
    
    def test_validate_markdown_format(self):
        """Test markdown format validation."""
        # Test valid format
        valid_content = '''# User AI Preferences

## Test Category

### Test Preference
- **Value**: `test`
- **Description**: Valid format
'''
        self.create_test_markdown_file(valid_content)
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        is_valid, issues = parser.validate_markdown_format()
        assert is_valid is True
        assert len(issues) == 0
        
        # Test invalid format (missing title)
        invalid_content = '''## Test Category

### Test Preference
- **Value**: `test`
'''
        self.create_test_markdown_file(invalid_content)
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        is_valid, issues = parser.validate_markdown_format()
        assert is_valid is False
        assert any("title" in issue.lower() for issue in issues)
        
        # Test missing categories
        no_categories = '''# User AI Preferences

Some content but no categories.
'''
        self.create_test_markdown_file(no_categories)
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        is_valid, issues = parser.validate_markdown_format()
        assert is_valid is False
        assert any("categories" in issue.lower() for issue in issues)
    
    def test_complex_real_world_example(self):
        """Test parsing a complex, real-world example."""
        content = '''# User AI Preferences

## Coding Style

### Indentation
- **Value**: `4 spaces`
- **Description**: Use 4 spaces for indentation instead of tabs

### Naming Convention
- **Value**: `snake_case`
- **Description**: Use snake_case for variable and function names

## Language & Framework Rules

### Primary Language
- **Value**: `Python`
- **Description**: Write code only in Python unless explicitly requested otherwise

### Web Framework
- **Value**: `FastAPI`
- **Description**: For web development, use the FastAPI framework

## Architecture Preferences

### Code Organization
- **Value**: `modular`
- **Description**: Organize code in small, focused modules

### Error Handling
- **Value**: `explicit`
- **Description**: Use explicit try-catch blocks and meaningful error messages

## General Instructions

### AI Persona
- **Value**: `senior_engineer`
- **Description**: Act as a senior software engineer with 10+ years experience

### Response Style
- **Value**: `concise_technical`
- **Description**: Provide concise, technically accurate responses with examples
'''
        self.create_test_markdown_file(content)
        
        parser = MarkdownPreferenceParser(self.test_markdown_file)
        preferences = parser.parse_preferences()
        
        # Should parse all preferences
        expected_keys = [
            "coding_style.indentation",
            "coding_style.naming_convention",
            "language_framework_rules.primary_language",
            "language_framework_rules.web_framework", 
            "architecture_preferences.code_organization",
            "architecture_preferences.error_handling",
            "general_instructions.ai_persona",
            "general_instructions.response_style"
        ]
        
        assert len(preferences) == len(expected_keys)
        for key in expected_keys:
            assert key in preferences
            assert "value" in preferences[key]
            assert "description" in preferences[key]
            assert "updated_at" in preferences[key]


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_markdown_file = os.path.join(self.temp_dir, "test_preferences.md")
        self.test_json_file = os.path.join(self.temp_dir, "test_preferences.json")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_preferences_from_markdown(self):
        """Test the convenience function for parsing preferences."""
        content = '''# User AI Preferences

## Test Category

### Test Preference
- **Value**: `convenience_test`
- **Description**: Testing convenience function
'''
        with open(self.test_markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        preferences = parse_preferences_from_markdown(self.test_markdown_file)
        assert "test_category.test_preference" in preferences
        assert preferences["test_category.test_preference"]["value"] == "convenience_test"
    
    def test_convert_markdown_to_json(self):
        """Test the convenience function for converting to JSON."""
        content = '''# User AI Preferences

## Test Category

### Test Preference
- **Value**: `json_conversion_test`
- **Description**: Testing JSON conversion
'''
        with open(self.test_markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        success = convert_markdown_to_json(self.test_markdown_file, self.test_json_file)
        assert success is True
        assert os.path.exists(self.test_json_file)
        
        # Verify JSON content
        with open(self.test_json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        assert "test_category.test_preference" in json_data
        assert json_data["test_category.test_preference"]["value"] == "json_conversion_test"
    
    def test_create_sample_preferences_file(self):
        """Test creating a sample preferences file."""
        sample_file = os.path.join(self.temp_dir, "sample_preferences.md")
        
        success = create_sample_preferences_file(sample_file)
        assert success is True
        assert os.path.exists(sample_file)
        
        # Verify the sample file can be parsed
        preferences = parse_preferences_from_markdown(sample_file)
        assert len(preferences) > 0
        
        # Should contain some expected preferences
        expected_categories = [
            "coding_style",
            "language_framework_rules", 
            "architecture_preferences",
            "general_instructions"
        ]
        
        found_categories = set()
        for key in preferences.keys():
            category = key.split('.')[0]
            found_categories.add(category)
        
        for expected_cat in expected_categories:
            assert expected_cat in found_categories


if __name__ == "__main__":
    pytest.main([__file__])