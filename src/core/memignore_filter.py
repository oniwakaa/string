"""
Simple .memignore-based File Filtering System

Provides user-controlled file filtering for codebase loading using .memignore files.
Completely replaces complex universal filtering with simple, extensible user control.

Key Features:
- .gitignore-style pattern matching using pathspec
- Minimal safe defaults (only excludes .git and similar meta-folders)
- Full user control over inclusions/exclusions
- Comprehensive logging of filtering decisions
- No hardcoded file type restrictions or size limits
"""

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

try:
    import pathspec
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False
    print("⚠️  pathspec not available. Install with: pip install pathspec")

logger = logging.getLogger(__name__)

@dataclass
class FilteringStats:
    """Statistics from .memignore filtering operation"""
    total_files_found: int = 0
    total_files_included: int = 0
    total_files_excluded: int = 0
    total_size_included: int = 0
    total_size_excluded: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)
    memignore_patterns_used: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0

class MemignoreFilter:
    """
    Simple file filtering system based on .memignore files.
    
    Provides complete user control over which files are included/excluded
    when loading codebases into memory, without complex universal filtering.
    """
    
    def __init__(self):
        self.stats = FilteringStats()
        self._pathspec = None
        self._memignore_path = None
        
        # Minimal safe defaults - only exclude obvious meta-directories
        self.minimal_safe_defaults = [
            ".git/",
            ".svn/", 
            ".hg/",
            ".bzr/"
        ]
        
    def load_memignore(self, project_root: Union[str, Path]) -> Tuple[List[str], bool]:
        """
        Load .memignore file patterns if it exists.
        
        Args:
            project_root: Root directory to search for .memignore
            
        Returns:
            Tuple of (patterns_list, memignore_exists)
        """
        if not PATHSPEC_AVAILABLE:
            logger.warning("pathspec not available - .memignore filtering disabled")
            return self.minimal_safe_defaults, False
            
        project_path = Path(project_root).resolve()
        memignore_path = project_path / ".memignore"
        
        patterns = []
        memignore_exists = False
        
        if memignore_path.exists():
            try:
                with open(memignore_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            patterns.append(line)
                
                memignore_exists = True
                self._memignore_path = str(memignore_path)
                logger.info(f"📋 Loaded {len(patterns)} patterns from .memignore")
                
                if patterns:
                    logger.debug("🔍 .memignore patterns:")
                    for pattern in patterns:
                        logger.debug(f"   {pattern}")
                        
            except Exception as e:
                logger.warning(f"⚠️  Failed to read .memignore file: {e}")
                patterns = self.minimal_safe_defaults
        else:
            logger.info("📋 No .memignore found - using minimal safe defaults")
            patterns = self.minimal_safe_defaults
            
        return patterns, memignore_exists
    
    def create_pathspec(self, patterns: List[str]) -> Optional[object]:
        """Create pathspec object for pattern matching"""
        if not PATHSPEC_AVAILABLE or not patterns:
            return None
            
        try:
            spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
            logger.debug(f"✅ Created pathspec with {len(patterns)} patterns")
            return spec
        except Exception as e:
            logger.warning(f"⚠️  Failed to create pathspec: {e}")
            return None
    
    def should_exclude_path(self, file_path: Path, project_root: Path, 
                           pathspec_obj: Optional[object]) -> Tuple[bool, str]:
        """
        Check if a file/directory should be excluded based on .memignore patterns.
        
        Args:
            file_path: File or directory path to check
            project_root: Project root directory
            pathspec_obj: Compiled pathspec object for pattern matching
            
        Returns:
            Tuple of (should_exclude, reason)
        """
        if not pathspec_obj:
            return False, ""
            
        try:
            # Get relative path from project root
            relative_path = file_path.relative_to(project_root)
            relative_str = str(relative_path)
            
            # Check if file/directory matches any .memignore pattern
            if pathspec_obj.match_file(relative_str):
                return True, f"memignore_pattern:{relative_str}"
                
            # For directories, also check with trailing slash
            if file_path.is_dir():
                dir_pattern = relative_str + "/"
                if pathspec_obj.match_file(dir_pattern):
                    return True, f"memignore_directory:{dir_pattern}"
                    
        except Exception as e:
            logger.debug(f"Error checking path {file_path}: {e}")
            return False, "check_error"
            
        return False, ""
    
    def filter_codebase_files(self, project_root: Union[str, Path],
                             custom_memignore_path: Optional[str] = None,
                             additional_patterns: Optional[List[str]] = None) -> List[Path]:
        """
        Main entry point: Filter codebase files using .memignore patterns.
        
        Args:
            project_root: Root directory of the project
            custom_memignore_path: Optional custom path to .memignore file
            additional_patterns: Optional additional patterns to apply
            
        Returns:
            List of file paths that should be loaded into memory
        """
        root_path = Path(project_root).resolve()
        if not root_path.exists():
            raise ValueError(f"Project root does not exist: {root_path}")
            
        # Reset stats
        self.stats = FilteringStats()
        start_time = time.time()
        
        logger.info(f"🔍 Starting .memignore-based codebase filtering: {root_path}")
        
        # Load .memignore patterns
        if custom_memignore_path:
            # Use custom .memignore file
            try:
                with open(custom_memignore_path, 'r', encoding='utf-8') as f:
                    patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                memignore_exists = True
                self._memignore_path = custom_memignore_path
                logger.info(f"📋 Using custom .memignore: {custom_memignore_path}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load custom .memignore: {e}")
                patterns, memignore_exists = self.load_memignore(root_path)
        else:
            patterns, memignore_exists = self.load_memignore(root_path)
            
        # Add any additional patterns
        if additional_patterns:
            patterns.extend(additional_patterns)
            logger.info(f"📋 Added {len(additional_patterns)} additional patterns")
            
        # Store patterns used for stats
        self.stats.memignore_patterns_used = patterns.copy()
        
        # Create pathspec for pattern matching
        pathspec_obj = self.create_pathspec(patterns)
        
        # Walk directory tree and filter files
        included_files = []
        excluded_dirs = set()  # Track excluded directories to avoid traversing them
        
        logger.info(f"🚶 Walking directory tree from: {root_path}")
        
        for root, dirs, files in os.walk(root_path):
            current_dir = Path(root)
            
            # Skip if current directory is in excluded set
            if any(current_dir.is_relative_to(excluded_dir) for excluded_dir in excluded_dirs):
                dirs.clear()  # Don't traverse subdirectories
                continue
                
            # Filter directories in-place to prevent traversal of excluded ones
            dirs_to_remove = []
            for dir_name in dirs:
                dir_path = current_dir / dir_name
                should_exclude, reason = self.should_exclude_path(dir_path, root_path, pathspec_obj)
                
                if should_exclude:
                    dirs_to_remove.append(dir_name)
                    excluded_dirs.add(dir_path)
                    self.stats.exclusion_reasons[reason] = self.stats.exclusion_reasons.get(reason, 0) + 1
                    logger.debug(f"🚫 Excluding directory: {dir_path} ({reason})")
                    
            # Remove excluded directories from traversal
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)
                
            # Process files in current directory
            for file_name in files:
                file_path = current_dir / file_name
                self.stats.total_files_found += 1
                
                try:
                    should_exclude, reason = self.should_exclude_path(file_path, root_path, pathspec_obj)
                    
                    if should_exclude:
                        self.stats.total_files_excluded += 1
                        self.stats.exclusion_reasons[reason] = self.stats.exclusion_reasons.get(reason, 0) + 1
                        try:
                            self.stats.total_size_excluded += file_path.stat().st_size
                        except OSError:
                            pass
                        logger.debug(f"🚫 Excluding file: {file_path} ({reason})")
                        continue
                        
                    # File is included
                    try:
                        file_size = file_path.stat().st_size
                        included_files.append(file_path)
                        self.stats.total_files_included += 1
                        self.stats.total_size_included += file_size
                        logger.debug(f"✅ Including file: {file_path} ({file_size} bytes)")
                    except OSError as e:
                        logger.warning(f"⚠️  Could not stat file {file_path}: {e}")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Error processing file {file_path}: {e}")
                    self.stats.exclusion_reasons["processing_error"] = self.stats.exclusion_reasons.get("processing_error", 0) + 1
                    
        # Calculate processing time
        self.stats.processing_time_seconds = time.time() - start_time
        
        # Log comprehensive results
        self._log_filtering_results(root_path, memignore_exists)
        
        # Validation warnings
        self._validate_results()
        
        return included_files
    
    def _log_filtering_results(self, project_root: Path, memignore_exists: bool):
        """Log comprehensive filtering results"""
        
        logger.info("📊 " + "="*70)
        logger.info("🎯 .MEMIGNORE FILTERING RESULTS")
        logger.info("📊 " + "="*70)
        logger.info(f"📁 Project: {project_root}")
        logger.info(f"📋 .memignore file: {'Found' if memignore_exists else 'Not found (using minimal defaults)'}")
        logger.info(f"🔍 Patterns applied: {len(self.stats.memignore_patterns_used)}")
        logger.info(f"⏱️  Processing time: {self.stats.processing_time_seconds:.2f}s")
        logger.info(f"📈 Total files found: {self.stats.total_files_found:,}")
        logger.info(f"✅ Files included: {self.stats.total_files_included:,}")
        logger.info(f"🚫 Files excluded: {self.stats.total_files_excluded:,}")
        logger.info(f"💾 Total size included: {self.stats.total_size_included / 1024 / 1024:.1f} MB")
        logger.info(f"🗑️  Total size excluded: {self.stats.total_size_excluded / 1024 / 1024:.1f} MB")
        
        if self.stats.memignore_patterns_used:
            logger.info(f"\n📋 .memignore patterns applied:")
            for i, pattern in enumerate(self.stats.memignore_patterns_used, 1):
                logger.info(f"   {i:2d}. {pattern}")
                
        if self.stats.exclusion_reasons:
            logger.info(f"\n🚫 Exclusion breakdown:")
            total_exclusions = sum(self.stats.exclusion_reasons.values())
            for reason, count in sorted(self.stats.exclusion_reasons.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_exclusions * 100) if total_exclusions > 0 else 0
                logger.info(f"   {reason}: {count:,} files ({percentage:.1f}%)")
                
        logger.info("📊 " + "="*70)
    
    def _validate_results(self):
        """Validate filtering results and issue warnings if needed"""
        
        # Warning if no files included
        if self.stats.total_files_included == 0:
            logger.warning("🚨 WARNING: No files were included after filtering!")
            logger.warning("   Check your .memignore patterns - they may be too restrictive.")
            logger.warning("   Consider reviewing or removing some exclusion patterns.")
            
        # Warning if very few files included compared to found
        elif self.stats.total_files_found > 0:
            inclusion_rate = self.stats.total_files_included / self.stats.total_files_found
            if inclusion_rate < 0.1:  # Less than 10% included
                logger.warning(f"🚨 WARNING: Very low inclusion rate ({inclusion_rate:.1%})")
                logger.warning("   Only a small fraction of found files were included.")
                logger.warning("   Review .memignore patterns to ensure important files aren't excluded.")
                
        # Info about large include sets
        if self.stats.total_files_included > 5000:
            logger.warning(f"ℹ️  INFO: Large file set included ({self.stats.total_files_included:,} files)")
            logger.warning("   Consider adding more exclusion patterns to .memignore if performance is impacted.")
            
        if self.stats.total_size_included > 100 * 1024 * 1024:  # 100MB
            logger.warning(f"ℹ️  INFO: Large total size ({self.stats.total_size_included / 1024 / 1024:.1f}MB)")
            logger.warning("   Large codebases may impact memory and processing performance.")
    
    def get_filtering_stats(self) -> FilteringStats:
        """Get current filtering statistics"""
        return self.stats
    
    def create_sample_memignore(self, project_root: Union[str, Path],
                               language_hints: Optional[List[str]] = None) -> str:
        """
        Create a sample .memignore file with common patterns.
        
        Args:
            project_root: Project root directory
            language_hints: Optional list of detected languages for better defaults
            
        Returns:
            String content for .memignore file
        """
        
        # Base patterns that apply to most projects
        base_patterns = [
            "# Version control",
            ".git/",
            ".svn/",
            ".hg/",
            "",
            "# Build outputs and dependencies", 
            "build/",
            "dist/",
            "out/",
            "target/",
            "node_modules/",
            "__pycache__/",
            "*.pyc",
            "",
            "# IDE and editor files",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "*~",
            "",
            "# Logs and temporary files",
            "*.log",
            "logs/",
            "tmp/",
            "temp/",
            "",
            "# Large binary files (uncomment as needed)",
            "# *.zip",
            "# *.tar.gz", 
            "# *.pdf",
            "# *.png",
            "# *.jpg",
            "",
            "# Add your project-specific patterns below:",
            "# examples:",
            "# data/",
            "# models/",
            "# *.db",
        ]
        
        # Add language-specific patterns if hints provided
        if language_hints:
            if 'python' in language_hints:
                base_patterns.extend([
                    "",
                    "# Python specific",
                    "venv/",
                    ".venv/",
                    "env/",
                    ".pytest_cache/",
                    ".coverage",
                    "htmlcov/",
                ])
                
            if 'javascript' in language_hints or 'typescript' in language_hints:
                base_patterns.extend([
                    "",
                    "# JavaScript/TypeScript specific", 
                    ".next/",
                    ".nuxt/",
                    "coverage/",
                    ".nyc_output/",
                ])
                
            if 'java' in language_hints:
                base_patterns.extend([
                    "",
                    "# Java specific",
                    "*.class",
                    "*.jar",
                    ".gradle/",
                    ".m2/",
                ])
                
        content = "\n".join(base_patterns)
        
        # Optionally write to file
        memignore_path = Path(project_root) / ".memignore"
        if not memignore_path.exists():
            try:
                with open(memignore_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"📝 Created sample .memignore at: {memignore_path}")
            except Exception as e:
                logger.warning(f"⚠️  Could not create .memignore file: {e}")
                
        return content

def create_memignore_documentation() -> str:
    """Generate documentation for .memignore usage"""
    
    docs = """
# .memignore File Documentation

The `.memignore` file controls which files and directories are excluded when loading 
your codebase into memory for AI assistance. It uses .gitignore-style patterns.

## Pattern Syntax

- `filename.txt` - exclude specific file
- `*.log` - exclude all .log files  
- `folder/` - exclude entire directory and contents
- `**/temp` - exclude any 'temp' directory at any level
- `!important.txt` - include file even if excluded by earlier pattern
- `# comment` - comments start with #

## Common Patterns

```
# Version control
.git/
.svn/

# Dependencies  
node_modules/
__pycache__/
venv/

# Build outputs
build/
dist/
target/

# IDE files
.vscode/
.idea/
*.swp

# Logs and temp files
*.log
logs/
tmp/

# Large binary files
*.zip
*.pdf
*.png
*.mp4
```

## Best Practices

1. **Start minimal** - only exclude what you're sure you don't need
2. **Test iteratively** - reload and check what files are included
3. **Use comments** - document why patterns exist
4. **Be specific** - prefer specific patterns over broad wildcards
5. **Review regularly** - update as project structure changes

## Troubleshooting

- **No files loaded**: Patterns too restrictive, remove some exclusions
- **Too many files**: Add more specific exclusion patterns  
- **Missing important files**: Check for overly broad patterns like `*`
- **Slow loading**: Exclude large binary directories and files

## Advanced Examples

```
# Exclude test files but keep integration tests
test/
!test/integration/

# Exclude data but keep small config files
data/
!data/config/
!data/*.json

# Language-specific exclusions
**/*.pyc
**/*.class
**/.DS_Store
```
"""
    
    return docs