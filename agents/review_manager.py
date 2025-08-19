"""
Interactive Review Manager for Agent File Operations

This module provides human-in-the-loop review capabilities for agent-proposed 
file changes, with terminal-friendly diff rendering and approval prompts.

Features:
- Terminal-friendly diff previews for create/edit operations
- Interactive approval prompts with bulk actions (Accept All/Reject All)
- Optional Rich syntax highlighting with plain-text fallback
- Configurable auto-approval for CI/non-interactive environments
- Integration with existing SecureToolbox safety guarantees

Author: Claude Code Assistant
Date: 2025-01-19
"""

import difflib
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import json

try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ReviewDecision(Enum):
    """Review decision types for file operations."""
    ACCEPT = "accept"
    REJECT = "reject"
    VIEW_MORE = "view_more"
    ACCEPT_ALL = "accept_all"
    REJECT_ALL = "reject_all"


class ReviewConfig:
    """Configuration for review behavior."""
    def __init__(
        self,
        interactive: bool = True,
        auto_approve: bool = False,
        show_full_diff: bool = False,
        max_preview_lines: int = 40,
        max_diff_hunks: int = 5
    ):
        self.interactive = interactive
        self.auto_approve = auto_approve
        self.show_full_diff = show_full_diff
        self.max_preview_lines = max_preview_lines
        self.max_diff_hunks = max_diff_hunks


class ReviewManager:
    """
    Manages interactive review of agent-proposed file changes.
    
    Provides terminal-friendly previews and approval workflows for file
    creation and editing operations before they are applied via SecureToolbox.
    """
    
    def __init__(self, config: Optional[ReviewConfig] = None):
        """
        Initialize ReviewManager with configuration.
        
        Args:
            config: Review configuration, defaults to interactive mode
        """
        self.config = config or ReviewConfig()
        self.console = Console() if RICH_AVAILABLE else None
        self.session_decisions = {
            'accept_all': False,
            'reject_all': False
        }
    
    def review_next_action(self, next_action: Dict[str, Any]) -> Tuple[ReviewDecision, Dict[str, Any]]:
        """
        Review a next_action payload and get user approval.
        
        Args:
            next_action: Tool command dict with 'tool' and 'args' keys
            
        Returns:
            Tuple of (decision, metadata) where metadata contains approval info
        """
        if not self._is_file_operation(next_action):
            # Non-file operations bypass review
            return ReviewDecision.ACCEPT, {'auto_approved': True, 'reason': 'non_file_operation'}
        
        if not self.config.interactive or self.config.auto_approve:
            return ReviewDecision.ACCEPT, {'auto_approved': True, 'reason': 'auto_approve_mode'}
        
        # Check session-level decisions
        if self.session_decisions['accept_all']:
            return ReviewDecision.ACCEPT, {'auto_approved': True, 'reason': 'session_accept_all'}
        
        if self.session_decisions['reject_all']:
            return ReviewDecision.REJECT, {'auto_approved': True, 'reason': 'session_reject_all'}
        
        # Interactive review
        try:
            preview_info = self._generate_preview(next_action)
            self._render_preview(preview_info)
            
            while True:
                decision = self._prompt_user()
                
                if decision == ReviewDecision.VIEW_MORE:
                    self._render_full_preview(preview_info)
                    continue
                elif decision == ReviewDecision.ACCEPT_ALL:
                    self.session_decisions['accept_all'] = True
                    return ReviewDecision.ACCEPT, {'user_approved': True, 'session_accept_all': True}
                elif decision == ReviewDecision.REJECT_ALL:
                    self.session_decisions['reject_all'] = True
                    return ReviewDecision.REJECT, {'user_rejected': True, 'session_reject_all': True}
                else:
                    user_approved = decision == ReviewDecision.ACCEPT
                    return decision, {'user_approved': user_approved}
                    
        except Exception as e:
            self._print_error(f"Review failed: {e}")
            # Fallback to rejection on error to maintain safety
            return ReviewDecision.REJECT, {'error': str(e), 'reason': 'review_error'}
    
    def reset_session_decisions(self):
        """Reset session-level Accept All/Reject All decisions."""
        self.session_decisions = {'accept_all': False, 'reject_all': False}
    
    def _is_file_operation(self, next_action: Dict[str, Any]) -> bool:
        """Check if the next_action is a file operation that requires review."""
        tool = next_action.get('tool', '')
        file_tools = {'create_file', 'edit_file', 'write_file', 'patch_file', 'replace_region'}
        return tool in file_tools
    
    def _generate_preview(self, next_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate preview information for a file operation.
        
        Args:
            next_action: Tool command to preview
            
        Returns:
            Dict with preview information (operation, path, content, diff, etc.)
        """
        tool = next_action.get('tool')
        args = next_action.get('args', {})
        
        file_path = args.get('file_path', 'unknown')
        content = args.get('content', '')
        
        preview = {
            'operation': tool,
            'file_path': file_path,
            'content': content,
            'file_exists': os.path.exists(file_path),
            'language': self._detect_language(file_path)
        }
        
        if tool == 'create_file':
            preview.update(self._preview_create(file_path, content))
        elif tool in ['edit_file', 'patch_file']:
            preview.update(self._preview_edit(file_path, content))
        
        return preview
    
    def _preview_create(self, file_path: str, content: str) -> Dict[str, Any]:
        """Generate preview for file creation."""
        lines = content.splitlines()
        total_lines = len(lines)
        
        # Show first/last N lines with ellipsis if too long
        if total_lines > self.config.max_preview_lines:
            preview_lines = int(self.config.max_preview_lines // 2)
            snippet_lines = (
                lines[:preview_lines] + 
                [f"... ({total_lines - 2*preview_lines} lines omitted) ..."] +
                lines[-preview_lines:]
            )
        else:
            snippet_lines = lines
        
        return {
            'total_lines': total_lines,
            'snippet_lines': snippet_lines,
            'full_content': content,
            'size_bytes': len(content.encode('utf-8'))
        }
    
    def _preview_edit(self, file_path: str, new_content: str) -> Dict[str, Any]:
        """Generate preview for file editing."""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            else:
                # File doesn't exist, treat as create
                return self._preview_create(file_path, new_content)
            
            # Generate unified diff
            original_lines = original_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            diff_lines = list(difflib.unified_diff(
                original_lines,
                new_lines,
                fromfile=f"{file_path} (original)",
                tofile=f"{file_path} (modified)",
                n=3
            ))
            
            if not diff_lines:
                # No changes detected
                return {
                    'no_changes': True,
                    'diff_lines': [],
                    'hunks_count': 0
                }
            
            # Count hunks and limit preview if needed
            hunks_count = sum(1 for line in diff_lines if line.startswith('@@'))
            
            if not self.config.show_full_diff and hunks_count > self.config.max_diff_hunks:
                # Truncate diff to max hunks
                truncated_diff = self._truncate_diff(diff_lines, self.config.max_diff_hunks)
                return {
                    'diff_lines': truncated_diff,
                    'full_diff_lines': diff_lines,
                    'hunks_count': hunks_count,
                    'truncated': True
                }
            else:
                return {
                    'diff_lines': diff_lines,
                    'full_diff_lines': diff_lines,
                    'hunks_count': hunks_count,
                    'truncated': False
                }
        
        except Exception as e:
            # Fallback to content preview if diff fails
            return {
                'error': str(e),
                'fallback_content': new_content[:1000] + '...' if len(new_content) > 1000 else new_content
            }
    
    def _truncate_diff(self, diff_lines: List[str], max_hunks: int) -> List[str]:
        """Truncate diff to maximum number of hunks."""
        result = []
        hunk_count = 0
        
        for line in diff_lines:
            result.append(line)
            if line.startswith('@@'):
                hunk_count += 1
                if hunk_count >= max_hunks:
                    remaining_hunks = sum(1 for l in diff_lines if l.startswith('@@')) - max_hunks
                    if remaining_hunks > 0:
                        result.append(f"... ({remaining_hunks} more hunks omitted) ...\n")
                    break
        
        return result
    
    def _render_preview(self, preview: Dict[str, Any]):
        """Render the preview to terminal."""
        operation = preview['operation']
        file_path = preview['file_path']
        
        if self.console and RICH_AVAILABLE:
            self._render_rich_preview(preview)
        else:
            self._render_plain_preview(preview)
    
    def _render_rich_preview(self, preview: Dict[str, Any]):
        """Render preview using Rich with syntax highlighting."""
        operation = preview['operation']
        file_path = preview['file_path']
        
        # Header
        title = f"🔍 {operation.upper()}: {file_path}"
        self.console.print(Panel(title, style="bold blue"))
        
        if operation == 'create_file':
            lines = preview.get('total_lines', 0)
            size = preview.get('size_bytes', 0)
            self.console.print(f"📄 Creating new file ({lines} lines, {size} bytes)")
            
            content = '\n'.join(preview.get('snippet_lines', []))
            if preview.get('language'):
                syntax = Syntax(content, preview['language'], theme="monokai", line_numbers=True)
                self.console.print(syntax)
            else:
                self.console.print(content)
        
        elif 'diff_lines' in preview:
            if preview.get('no_changes'):
                self.console.print("✅ No changes detected (file content already matches)", style="green")
            else:
                hunks = preview.get('hunks_count', 0)
                truncated = preview.get('truncated', False)
                status = f"📝 Editing file ({hunks} hunks)"
                if truncated:
                    status += f" - showing first {self.config.max_diff_hunks} hunks"
                self.console.print(status)
                
                diff_text = ''.join(preview['diff_lines'])
                # Use simple syntax highlighting for diffs
                syntax = Syntax(diff_text, "diff", theme="monokai")
                self.console.print(syntax)
    
    def _render_plain_preview(self, preview: Dict[str, Any]):
        """Render preview in plain text for terminals without Rich."""
        operation = preview['operation']
        file_path = preview['file_path']
        
        print(f"\n{'='*60}")
        print(f"REVIEW: {operation.upper()} - {file_path}")
        print(f"{'='*60}")
        
        if operation == 'create_file':
            lines = preview.get('total_lines', 0)
            size = preview.get('size_bytes', 0)
            print(f"Creating new file ({lines} lines, {size} bytes)")
            print("-" * 40)
            
            snippet_lines = preview.get('snippet_lines', [])
            for i, line in enumerate(snippet_lines):
                print(f"{i+1:4d} | {line}")
        
        elif 'diff_lines' in preview:
            if preview.get('no_changes'):
                print("No changes detected (file content already matches)")
            else:
                hunks = preview.get('hunks_count', 0)
                truncated = preview.get('truncated', False)
                status = f"Editing file ({hunks} hunks)"
                if truncated:
                    status += f" - showing first {self.config.max_diff_hunks} hunks"
                print(status)
                print("-" * 40)
                
                for line in preview['diff_lines']:
                    print(line.rstrip())
        
        print("-" * 60)
    
    def _render_full_preview(self, preview: Dict[str, Any]):
        """Render the full preview (used for 'view more' option)."""
        if preview['operation'] == 'create_file':
            content = preview.get('full_content', '')
            if self.console and RICH_AVAILABLE and preview.get('language'):
                syntax = Syntax(content, preview['language'], theme="monokai", line_numbers=True)
                self.console.print(Panel(syntax, title="Full File Content"))
            else:
                print("\n" + "="*60)
                print("FULL FILE CONTENT:")
                print("="*60)
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    print(f"{i:4d} | {line}")
                print("="*60)
        
        elif 'full_diff_lines' in preview:
            full_diff = ''.join(preview['full_diff_lines'])
            if self.console and RICH_AVAILABLE:
                syntax = Syntax(full_diff, "diff", theme="monokai")
                self.console.print(Panel(syntax, title="Full Diff"))
            else:
                print("\n" + "="*60)
                print("FULL DIFF:")
                print("="*60)
                print(full_diff)
                print("="*60)
    
    def _prompt_user(self) -> ReviewDecision:
        """Prompt user for approval decision."""
        prompt = (
            "\nChoose an action:\n"
            "  [a]ccept - Apply this change\n"
            "  [r]eject - Skip this change\n"
            "  [v]iew   - View full diff/content\n"
            "  [A]ccept all remaining changes\n"
            "  [R]eject all remaining changes\n"
            "\nEnter choice (a/r/v/A/R): "
        )
        
        try:
            choice = input(prompt).strip().lower()
            
            if choice == 'a':
                return ReviewDecision.ACCEPT
            elif choice == 'r':
                return ReviewDecision.REJECT
            elif choice == 'v':
                return ReviewDecision.VIEW_MORE
            elif choice == 'A':
                return ReviewDecision.ACCEPT_ALL
            elif choice == 'R':
                return ReviewDecision.REJECT_ALL
            else:
                print("Invalid choice. Please enter 'a', 'r', 'v', 'A', or 'R'.")
                return self._prompt_user()
                
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            return ReviewDecision.REJECT
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.sql': 'sql',
            '.sh': 'bash',
            '.md': 'markdown'
        }
        
        return language_map.get(ext)
    
    def _print_error(self, message: str):
        """Print error message to stderr."""
        if self.console and RICH_AVAILABLE:
            self.console.print(f"❌ {message}", style="red", file=sys.stderr)
        else:
            print(f"ERROR: {message}", file=sys.stderr)


# Convenience functions for common use cases
def create_review_manager(interactive: bool = True, auto_approve: bool = False) -> ReviewManager:
    """Create a ReviewManager with common configuration."""
    config = ReviewConfig(interactive=interactive, auto_approve=auto_approve)
    return ReviewManager(config)


def review_file_operation(next_action: Dict[str, Any], config: Optional[ReviewConfig] = None) -> Tuple[ReviewDecision, Dict[str, Any]]:
    """
    Quick function to review a single file operation.
    
    Args:
        next_action: Tool command to review
        config: Optional review configuration
        
    Returns:
        Tuple of (decision, metadata)
    """
    manager = ReviewManager(config)
    return manager.review_next_action(next_action)


# Example usage
if __name__ == "__main__":
    # Example create file action
    create_action = {
        "tool": "create_file",
        "args": {
            "file_path": "example.py",
            "content": "def hello_world():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello_world()\n"
        }
    }
    
    # Example edit file action  
    edit_action = {
        "tool": "edit_file",
        "args": {
            "file_path": "existing_file.py",
            "content": "def updated_function():\n    return 'updated'\n"
        }
    }
    
    # Demo the review process
    manager = create_review_manager(interactive=True)
    
    print("🔍 Testing ReviewManager with example file operations")
    print("=" * 60)
    
    # Test create file review
    decision, metadata = manager.review_next_action(create_action)
    print(f"Create decision: {decision}, metadata: {metadata}")
    
    # Test edit file review  
    decision, metadata = manager.review_next_action(edit_action)
    print(f"Edit decision: {decision}, metadata: {metadata}")