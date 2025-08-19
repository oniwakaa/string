"""
Content Sanitizer - Remove chat artifacts and Markdown formatting from model outputs
before writing to files.

This module provides utilities to clean model-generated content by:
- Extracting code from fenced code blocks when present
- Removing chat markers and non-code prose
- Preserving shebangs and essential imports
- Ensuring idempotent processing
"""

import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ContentSanitizer:
    """Sanitizes model outputs to extract clean code content."""
    
    # Patterns for detecting code-like content
    CODE_INDICATORS = [
        r'^import\s+\w+',  # Python imports
        r'^from\s+\w+\s+import',  # Python from imports
        r'^def\s+\w+\(',  # Function definitions
        r'^class\s+\w+\(?',  # Class definitions
        r'^#!\/.*',  # Shebang lines
        r'^\s*[a-zA-Z_]\w*\s*=',  # Variable assignments
        r'^\s*if\s+.*:',  # If statements
        r'^\s*for\s+.*:',  # For loops
        r'^\s*while\s+.*:',  # While loops
        r'^\s*try\s*:',  # Try blocks
        r'^\s*except\s+.*:',  # Exception handlers
    ]
    
    # Patterns for chat artifacts to remove
    CHAT_ARTIFACTS = [
        r'^<end_of_turn>.*',
        r'^<start_of_turn>.*',
        r'^user\s*$',
        r'^assistant\s*$',
        r'^model\s*$',
        r'^Based on.*?,\s*',
        r'^Here\'s\s+.*:',
        r'^I\'ll\s+.*',
        r'^Let me\s+.*',
        r'^This\s+code\s+.*',
        r'^The\s+following\s+.*',
        r'^```\w*\s*$',  # Fence markers without content
        r'^```\s*$',
        r'^\*\*.*\*\*\s*$',  # Markdown bold headers
        r'^#\s+.*$',  # Markdown headers (but preserve comments in code)
    ]

    def __init__(self):
        self.code_pattern = re.compile('|'.join(self.CODE_INDICATORS), re.MULTILINE | re.IGNORECASE)
        self.artifact_patterns = [re.compile(pattern, re.MULTILINE | re.IGNORECASE) 
                                for pattern in self.CHAT_ARTIFACTS]

    def extract_fenced_code(self, content: str) -> Optional[str]:
        """Extract code from fenced code blocks if present."""
        # Look for fenced code blocks (```lang...code...```)
        fenced_pattern = r'```(?:\w+)?\s*\n(.*?)\n```'
        matches = re.findall(fenced_pattern, content, re.DOTALL | re.MULTILINE)
        
        if matches:
            # Return the first substantial code block
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 10 and self._is_code_like(cleaned):
                    return cleaned
        return None

    def _is_code_like(self, text: str) -> bool:
        """Heuristic to determine if text looks like code."""
        lines = text.strip().split('\n')
        if not lines:
            return False
            
        code_lines = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):  # Comments are code-like
                continue
            if self.code_pattern.search(line):
                code_lines += 1
        
        # Consider it code-like if >30% of non-comment lines match patterns
        non_empty_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        if non_empty_lines == 0:
            return False
        return (code_lines / non_empty_lines) > 0.3

    def _preserve_essential_elements(self, content: str) -> List[str]:
        """Extract shebang and import statements to preserve."""
        lines = content.split('\n')
        essential = []
        
        for line in lines:
            stripped = line.strip()
            # Preserve shebang
            if stripped.startswith('#!'):
                essential.append(line)
            # Preserve imports
            elif stripped.startswith('import ') or stripped.startswith('from '):
                essential.append(line)
        
        return essential

    def _remove_chat_artifacts(self, content: str) -> str:
        """Remove chat markers and conversation artifacts."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines at start
            if not cleaned_lines and not line.strip():
                continue
                
            # Check if line matches any artifact pattern
            is_artifact = False
            for pattern in self.artifact_patterns:
                if pattern.match(line):
                    is_artifact = True
                    break
            
            if not is_artifact:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def sanitize(self, content: str, preserve_structure: bool = True) -> str:
        """
        Sanitize model output to extract clean code content.
        
        Args:
            content: Raw model output text
            preserve_structure: Whether to preserve code structure and formatting
            
        Returns:
            Cleaned code content suitable for file writing
        """
        if not content or not content.strip():
            return ""
        
        # Step 1: Try to extract from fenced code blocks first
        fenced_code = self.extract_fenced_code(content)
        if fenced_code:
            logger.debug("Extracted code from fenced block")
            return fenced_code
        
        # Step 2: Extract essential elements before cleaning
        essential_elements = self._preserve_essential_elements(content)
        
        # Step 3: Remove chat artifacts
        cleaned_content = self._remove_chat_artifacts(content)
        
        # Step 4: If we have essential elements, ensure they're at the top
        if essential_elements and preserve_structure:
            remaining_lines = []
            content_lines = cleaned_content.split('\n')
            
            # Skip lines that are already in essential elements
            for line in content_lines:
                if line not in essential_elements:
                    remaining_lines.append(line)
            
            # Combine essential elements at top with remaining content
            result_lines = essential_elements + [''] + remaining_lines
            cleaned_content = '\n'.join(result_lines)
        
        # Step 5: Final cleanup - remove excessive whitespace but preserve structure
        lines = cleaned_content.split('\n')
        final_lines = []
        prev_empty = False
        
        for line in lines:
            # Collapse multiple empty lines to single empty line
            if not line.strip():
                if not prev_empty:
                    final_lines.append('')
                prev_empty = True
            else:
                final_lines.append(line)
                prev_empty = False
        
        result = '\n'.join(final_lines).strip()
        
        # Ensure we have some actual content
        if not result or len(result) < 5:
            logger.warning("Sanitizer produced minimal content, returning original")
            return content.strip()
        
        return result

    def is_content_clean(self, content: str) -> bool:
        """Check if content appears to already be clean (for idempotency)."""
        # Check for common chat artifacts
        for pattern in self.artifact_patterns:
            if pattern.search(content):
                return False
        
        # Check for fenced code blocks
        if '```' in content:
            return False
            
        return True


# Global instance for convenience
_sanitizer = ContentSanitizer()

def sanitize_content(content: str, preserve_structure: bool = True) -> str:
    """Convenience function to sanitize content using global sanitizer."""
    return _sanitizer.sanitize(content, preserve_structure)

def is_content_clean(content: str) -> bool:
    """Convenience function to check if content is already clean."""
    return _sanitizer.is_content_clean(content)