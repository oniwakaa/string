"""
Intelligent Codebase File Filtering System

Solves the MemOS embedding loop by implementing:
1. Cross-language file pattern recognition
2. Universal exclusion patterns and directory rules  
3. Intelligent recursive traversal with size limits
4. Extensible .memignore support
5. Comprehensive logging and monitoring

This prevents processing of irrelevant files (dependencies, binaries, caches) 
while intelligently detecting and including only relevant source code files.
"""

import fnmatch
import hashlib
import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import yaml

logger = logging.getLogger(__name__)

@dataclass
class ProjectLanguageHints:
    """Detected project language configuration hints"""
    detected_languages: Set[str] = field(default_factory=set)
    config_files: Dict[str, str] = field(default_factory=dict)  # file_name -> language
    package_managers: Set[str] = field(default_factory=set)
    build_systems: Set[str] = field(default_factory=set)

@dataclass  
class FilteringStats:
    """Statistics from file filtering operation"""
    total_files_found: int = 0
    total_files_included: int = 0
    total_files_excluded: int = 0
    total_size_included: int = 0
    total_size_excluded: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    language_breakdown: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
class CodebaseFilter:
    """
    Intelligent file filtering system for codebase loading.
    
    Features:
    - Cross-language source file detection
    - Universal exclusion of dependencies, build artifacts, binaries
    - Smart directory traversal with size limits
    - .memignore support for project-specific rules
    - Comprehensive logging and audit trails
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.stats = FilteringStats()
        self._language_hints = None
        self._exclusion_cache = {}
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load filtering configuration from file or use defaults"""
        
        default_config = {
            # Cross-language file extensions for source code
            "source_extensions": {
                "python": [".py", ".pyw", ".pyi"],
                "javascript": [".js", ".jsx", ".mjs", ".cjs"],
                "typescript": [".ts", ".tsx", ".d.ts"],
                "java": [".java", ".kt", ".scala"],
                "cpp": [".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"],
                "csharp": [".cs", ".vb"],
                "go": [".go"],
                "rust": [".rs"],
                "php": [".php", ".phtml"],
                "ruby": [".rb", ".rake"],
                "swift": [".swift"],
                "dart": [".dart"],
                "kotlin": [".kt", ".kts"],
                "r": [".r", ".R"],
                "julia": [".jl"],
                "lua": [".lua"],
                "perl": [".pl", ".pm"],
                "shell": [".sh", ".bash", ".zsh", ".fish"],
                "powershell": [".ps1", ".psm1"],
                "sql": [".sql"],
                "markup": [".html", ".htm", ".xml", ".xhtml"],
                "css": [".css", ".scss", ".sass", ".less"],
                "config": [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"],
                "docs": [".md", ".txt", ".rst", ".adoc"]
            },
            
            # Language detection hints from project files
            "language_detection": {
                "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "poetry.lock"],
                "javascript": ["package.json", "package-lock.json", "yarn.lock"],
                "typescript": ["tsconfig.json", "tslint.json"],
                "java": ["pom.xml", "build.gradle", "gradle.properties"],
                "cpp": ["CMakeLists.txt", "Makefile", "configure.ac"],
                "csharp": ["*.csproj", "*.sln", "packages.config"],
                "go": ["go.mod", "go.sum"],
                "rust": ["Cargo.toml", "Cargo.lock"],
                "php": ["composer.json", "composer.lock"],
                "ruby": ["Gemfile", "Gemfile.lock", "*.gemspec"],
                "swift": ["Package.swift", "*.xcodeproj"],
                "dart": ["pubspec.yaml", "pubspec.lock"],
                "r": ["DESCRIPTION", "NAMESPACE"],
                "julia": ["Project.toml", "Manifest.toml"]
            },
            
            # Universal exclusion patterns (directories)
            "excluded_directories": [
                # Version control
                ".git", ".svn", ".hg", ".bzr",
                
                # Dependencies and packages
                "node_modules", "bower_components", "jspm_packages",
                "venv", "env", ".venv", ".env", "virtualenv",
                "site-packages", "dist-packages", "__pycache__",
                "vendor", "third_party", "3rdparty", "external",
                "target", "build", "dist", "out", "bin", "obj",
                
                # IDE and editor files  
                ".vscode", ".idea", ".vs", ".atom", ".sublime",
                "*.xcworkspace", "*.xcodeproj",
                
                # Test and coverage artifacts
                ".pytest_cache", ".coverage", "htmlcov", "coverage",
                ".nyc_output", "test-results", ".jest",
                
                # Logs and temporary files
                "logs", "log", "tmp", "temp", ".tmp", ".temp",
                "cache", ".cache", ".sass-cache",
                
                # Build systems and artifacts
                ".gradle", ".m2", ".maven", "gradle", 
                ".cargo", "target",
                ".next", ".nuxt", "dist", "build",
                
                # Databases and storage
                "qdrant_storage", "*.db", "*.sqlite", "*.sqlite3",
                "data", "datasets", "models", "weights",
                
                # Documentation build artifacts
                "_site", "_build", ".jekyll-cache", "site",
                "docs/_build", "doc/_build"
            ],
            
            # File patterns to exclude (globs)
            "excluded_file_patterns": [
                # Compiled and binary files
                "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dylib", "*.dll", "*.exe",
                "*.class", "*.jar", "*.war", "*.ear",
                "*.o", "*.obj", "*.lib", "*.a",
                
                # Archives and compressed files
                "*.zip", "*.tar", "*.tar.gz", "*.tgz", "*.rar", "*.7z",
                
                # Media files
                "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
                "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wav",
                "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx", "*.ppt", "*.pptx",
                
                # Log files
                "*.log", "*.out", "*.err",
                
                # Lock and temporary files
                "*.lock", "*.pid", "*.tmp", "*.temp", "*.swp", "*.swo",
                "*~", "#*#", ".#*",
                
                # Package manager files (sometimes large)
                "yarn.lock", "package-lock.json", "poetry.lock", "Pipfile.lock",
                "Cargo.lock", "composer.lock", "Gemfile.lock"
            ],
            
            # Size limits (in bytes)
            "max_file_size": 1024 * 1024,  # 1MB per file
            "max_total_size": 100 * 1024 * 1024,  # 100MB total
            "max_files_per_dir": 1000,  # Max files in single directory
            
            # Performance settings
            "enable_size_warnings": True,
            "enable_file_hashing": False,  # For duplicate detection
            "max_depth": 10  # Maximum directory traversal depth
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                        user_config = yaml.safe_load(f)
                    else:
                        user_config = json.load(f)
                
                # Merge user config with defaults
                default_config.update(user_config)
                logger.info(f"Loaded filtering config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def detect_project_languages(self, project_root: Union[str, Path]) -> ProjectLanguageHints:
        """Detect project languages by scanning for configuration files"""
        
        root_path = Path(project_root)
        hints = ProjectLanguageHints()
        
        # Scan for language detection files
        for lang, patterns in self.config["language_detection"].items():
            for pattern in patterns:
                # Handle glob patterns
                if '*' in pattern:
                    matches = list(root_path.glob(pattern))
                    if matches:
                        hints.detected_languages.add(lang)
                        for match in matches:
                            hints.config_files[match.name] = lang
                else:
                    # Direct file check
                    if (root_path / pattern).exists():
                        hints.detected_languages.add(lang)
                        hints.config_files[pattern] = lang
        
        # Add package managers and build systems based on detected files
        package_manager_map = {
            "package.json": "npm/yarn",
            "requirements.txt": "pip", 
            "Pipfile": "pipenv",
            "poetry.lock": "poetry",
            "Cargo.toml": "cargo",
            "go.mod": "go modules",
            "pom.xml": "maven",
            "build.gradle": "gradle",
            "Gemfile": "bundler",
            "composer.json": "composer"
        }
        
        for config_file in hints.config_files:
            if config_file in package_manager_map:
                hints.package_managers.add(package_manager_map[config_file])
        
        # If no languages detected, default to common ones
        if not hints.detected_languages:
            logger.warning("No project languages detected, using default extensions")
            hints.detected_languages.update(["python", "javascript", "config", "docs"])
        
        logger.info(f"Detected project languages: {sorted(hints.detected_languages)}")
        logger.info(f"Package managers: {sorted(hints.package_managers)}")
        
        self._language_hints = hints
        return hints
    
    def get_allowed_extensions(self, languages: Optional[Set[str]] = None) -> Set[str]:
        """Get allowed file extensions based on detected or specified languages"""
        
        if languages is None:
            if self._language_hints:
                languages = self._language_hints.detected_languages
            else:
                languages = {"python", "javascript", "config", "docs"}  # Defaults
        
        allowed_extensions = set()
        
        for lang in languages:
            if lang in self.config["source_extensions"]:
                allowed_extensions.update(self.config["source_extensions"][lang])
        
        # Always include common config and doc extensions
        allowed_extensions.update(self.config["source_extensions"]["config"])
        allowed_extensions.update(self.config["source_extensions"]["docs"])
        
        return allowed_extensions
    
    def load_memignore(self, project_root: Union[str, Path]) -> List[str]:
        """Load .memignore file patterns if it exists"""
        
        memignore_path = Path(project_root) / ".memignore"
        patterns = []
        
        if memignore_path.exists():
            try:
                with open(memignore_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
                
                logger.info(f"Loaded {len(patterns)} patterns from .memignore")
            except Exception as e:
                logger.warning(f"Failed to load .memignore: {e}")
        
        return patterns
    
    def should_exclude_directory(self, dir_path: Path, project_root: Path, 
                                memignore_patterns: List[str]) -> Tuple[bool, str]:
        """Check if directory should be excluded"""
        
        dir_name = dir_path.name
        relative_path = str(dir_path.relative_to(project_root))
        
        # Check against excluded directories
        for pattern in self.config["excluded_directories"]:
            if fnmatch.fnmatch(dir_name, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True, f"excluded_directory:{pattern}"
        
        # Check against .memignore patterns
        for pattern in memignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(dir_name, pattern):
                return True, f"memignore:{pattern}"
        
        return False, ""
    
    def should_exclude_file(self, file_path: Path, project_root: Path,
                           allowed_extensions: Set[str], memignore_patterns: List[str]) -> Tuple[bool, str]:
        """Check if file should be excluded"""
        
        file_name = file_path.name
        file_ext = file_path.suffix.lower()
        relative_path = str(file_path.relative_to(project_root))
        
        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.config["max_file_size"]:
                return True, f"oversized:{file_size}"
        except OSError:
            return True, "stat_error"
        
        # Check against excluded file patterns
        for pattern in self.config["excluded_file_patterns"]:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True, f"excluded_pattern:{pattern}"
        
        # Check extension allowlist
        if file_ext and file_ext not in allowed_extensions:
            return True, f"extension_not_allowed:{file_ext}"
        
        # Check against .memignore patterns
        for pattern in memignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(file_name, pattern):
                return True, f"memignore:{pattern}"
        
        return False, ""
    
    def filter_codebase_files(self, project_root: Union[str, Path],
                             custom_languages: Optional[Set[str]] = None) -> List[Path]:
        """
        Main entry point: Filter codebase files intelligently.
        
        Returns list of file paths that should be loaded into MemOS.
        """
        
        root_path = Path(project_root).resolve()
        if not root_path.exists():
            raise ValueError(f"Project root does not exist: {root_path}")
        
        # Reset stats
        self.stats = FilteringStats()
        start_time = time.time()
        
        logger.info(f"🔍 Starting intelligent codebase filtering: {root_path}")
        
        # Detect project languages
        if custom_languages:
            self._language_hints = ProjectLanguageHints(detected_languages=custom_languages)
        else:
            self.detect_project_languages(root_path)
        
        # Get allowed extensions and load .memignore
        allowed_extensions = self.get_allowed_extensions()
        memignore_patterns = self.load_memignore(root_path)
        
        logger.info(f"📁 Allowed extensions: {sorted(allowed_extensions)}")
        logger.info(f"🚫 Exclusion patterns: {len(memignore_patterns)} custom + {len(self.config['excluded_directories'])} default dirs")
        
        # Traverse and filter files
        included_files = []
        total_size = 0
        
        for root, dirs, files in os.walk(root_path):
            current_dir = Path(root)
            depth = len(current_dir.relative_to(root_path).parts)
            
            # Check depth limit
            if depth > self.config["max_depth"]:
                dirs.clear()  # Stop descending
                continue
            
            # Filter directories in-place to prevent traversal
            dirs_to_remove = []
            for dir_name in dirs:
                dir_path = current_dir / dir_name
                should_exclude, reason = self.should_exclude_directory(dir_path, root_path, memignore_patterns)
                
                if should_exclude:
                    dirs_to_remove.append(dir_name)
                    self.stats.exclusion_reasons[reason] += 1
                    logger.debug(f"Excluding directory: {dir_path} ({reason})")
            
            # Remove excluded directories
            for dir_name in dirs_to_remove:
                dirs.remove(dir_name)
            
            # Check files per directory limit
            if len(files) > self.config["max_files_per_dir"]:
                logger.warning(f"🚨 Directory {current_dir} has {len(files)} files (limit: {self.config['max_files_per_dir']})")
                if self.config["enable_size_warnings"]:
                    files = files[:self.config["max_files_per_dir"]]  # Truncate
            
            # Process files in current directory
            for file_name in files:
                file_path = current_dir / file_name
                self.stats.total_files_found += 1
                
                try:
                    should_exclude, reason = self.should_exclude_file(
                        file_path, root_path, allowed_extensions, memignore_patterns
                    )
                    
                    if should_exclude:
                        self.stats.total_files_excluded += 1
                        self.stats.exclusion_reasons[reason] += 1
                        try:
                            self.stats.total_size_excluded += file_path.stat().st_size
                        except OSError:
                            pass
                        continue
                    
                    # File is included
                    file_size = file_path.stat().st_size
                    file_ext = file_path.suffix.lower()
                    
                    # Check total size limit
                    if total_size + file_size > self.config["max_total_size"]:
                        logger.warning(f"🚨 Total size limit reached ({self.config['max_total_size']} bytes)")
                        break
                    
                    included_files.append(file_path)
                    self.stats.total_files_included += 1
                    self.stats.total_size_included += file_size
                    self.stats.language_breakdown[file_ext] += 1
                    total_size += file_size
                    
                    logger.debug(f"Including file: {file_path} ({file_size} bytes)")
                    
                except OSError as e:
                    logger.warning(f"Error processing file {file_path}: {e}")
                    self.stats.exclusion_reasons["os_error"] += 1
        
        # Log comprehensive results
        elapsed = time.time() - start_time
        self._log_filtering_results(elapsed, root_path)
        
        return included_files
    
    def _log_filtering_results(self, elapsed_time: float, project_root: Path):
        """Log comprehensive filtering results and statistics"""
        
        logger.info("📊 " + "="*60)
        logger.info("🎯 CODEBASE FILTERING RESULTS")
        logger.info("📊 " + "="*60)
        logger.info(f"📁 Project: {project_root}")
        logger.info(f"⏱️  Processing time: {elapsed_time:.2f}s")
        logger.info(f"🔍 Total files found: {self.stats.total_files_found:,}")
        logger.info(f"✅ Files included: {self.stats.total_files_included:,}")
        logger.info(f"🚫 Files excluded: {self.stats.total_files_excluded:,}")
        logger.info(f"💾 Total size included: {self.stats.total_size_included / 1024 / 1024:.1f} MB")
        logger.info(f"🗑️  Total size excluded: {self.stats.total_size_excluded / 1024 / 1024:.1f} MB")
        
        if self.stats.exclusion_reasons:
            logger.info("\n🚫 Exclusion breakdown:")
            for reason, count in sorted(self.stats.exclusion_reasons.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {reason}: {count:,} files")
        
        if self.stats.language_breakdown:
            logger.info("\n📋 File type breakdown:")
            for ext, count in sorted(self.stats.language_breakdown.items(), key=lambda x: x[1], reverse=True):
                ext_display = ext if ext else "(no extension)"
                logger.info(f"   {ext_display}: {count:,} files")
        
        # Warnings for potential issues
        if self.stats.total_files_included == 0:
            logger.warning("🚨 No files were included! Check filtering configuration.")
        elif self.stats.total_files_included > 10000:
            logger.warning(f"🚨 High file count ({self.stats.total_files_included:,}). Consider stricter filtering.")
        
        if self.stats.total_size_included > 50 * 1024 * 1024:  # 50MB
            logger.warning(f"🚨 Large total size ({self.stats.total_size_included / 1024 / 1024:.1f}MB). May impact performance.")
        
        logger.info("📊 " + "="*60)
    
    def get_filtering_stats(self) -> FilteringStats:
        """Get current filtering statistics"""
        return self.stats
    
    def create_audit_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Create detailed audit report of filtering results"""
        
        report = {
            "timestamp": time.time(),
            "project_languages": list(self._language_hints.detected_languages) if self._language_hints else [],
            "config_files": self._language_hints.config_files if self._language_hints else {},
            "filtering_stats": {
                "total_files_found": self.stats.total_files_found,
                "total_files_included": self.stats.total_files_included,
                "total_files_excluded": self.stats.total_files_excluded,
                "total_size_included_mb": self.stats.total_size_included / 1024 / 1024,
                "total_size_excluded_mb": self.stats.total_size_excluded / 1024 / 1024,
                "exclusion_reasons": dict(self.stats.exclusion_reasons),
                "language_breakdown": dict(self.stats.language_breakdown)
            },
            "configuration": {
                "max_file_size_mb": self.config["max_file_size"] / 1024 / 1024,
                "max_total_size_mb": self.config["max_total_size"] / 1024 / 1024,
                "max_depth": self.config["max_depth"]
            }
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📋 Audit report saved to: {output_path}")
        
        return report