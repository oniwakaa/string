"""
Utils package for the AI Coding Assistant.

This package contains utility modules for various functionality
including preference parsing and configuration management.
"""

from .preference_parser import (
    MarkdownPreferenceParser,
    parse_preferences_from_markdown,
    convert_markdown_to_json,
    create_sample_preferences_file
)

__all__ = [
    'MarkdownPreferenceParser',
    'parse_preferences_from_markdown', 
    'convert_markdown_to_json',
    'create_sample_preferences_file'
]