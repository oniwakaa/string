#!/usr/bin/env python3
"""
Project-Aware File Monitor

This module implements intelligent automatic codebase syncing that updates
the correct project's MemCube when files are changed. It features:

- Project-aware monitoring of workspace directories
- Intelligent project_id extraction from file paths
- Targeted ingestion to specific MemCubes
- Debouncing to handle rapid file saves efficiently
- Integration with the dynamic MemCube lifecycle system

Author: Claude Code Assistant
Date: 2024-12-19
"""

import asyncio
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass
from collections import defaultdict
from threading import Timer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object
    FileSystemEvent = object

from project_memory_manager import ProjectMemoryManager, MEMOS_AVAILABLE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FileChangeEvent:
    """Represents a file change event with project context."""
    file_path: str
    project_id: str
    user_id: str
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    timestamp: float
    src_path: Optional[str] = None  # For move events
    dest_path: Optional[str] = None  # For move events


class ProjectAwareFileHandler(FileSystemEventHandler):
    """
    Enhanced file system event handler that extracts project context
    and implements intelligent debouncing for efficient processing.
    """
    
    def __init__(
        self, 
        workspace_root: str,
        project_memory_manager: ProjectMemoryManager,
        debounce_delay: float = 0.5,
        user_id_extractor: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize the project-aware file handler.
        
        Args:
            workspace_root: Root directory containing project subdirectories
            project_memory_manager: Instance for managing project memories
            debounce_delay: Delay in seconds for debouncing rapid changes
            user_id_extractor: Function to extract user_id from paths (optional)
        """
        super().__init__()
        
        self.workspace_root = Path(workspace_root).resolve()
        self.project_memory_manager = project_memory_manager
        self.debounce_delay = debounce_delay
        self.user_id_extractor = user_id_extractor or self._default_user_id_extractor
        
        # Debouncing state
        self.pending_events: Dict[str, FileChangeEvent] = {}  # {file_path: latest_event}
        self.debounce_timers: Dict[str, Timer] = {}  # {file_path: timer}
        
        # File filters
        self.monitored_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.kt', '.swift', '.dart', '.scala',
            '.r', '.sql', '.sh', '.bash', '.ps1', '.yml', '.yaml', '.json', '.xml',
            '.html', '.css', '.scss', '.less', '.md', '.rst', '.txt', '.toml', '.ini'
        }
        
        self.excluded_dirs = {
            '__pycache__', '.git', '.svn', '.hg', 'node_modules', '.venv', 'venv',
            '.env', 'dist', 'build', 'target', 'bin', 'obj', '.DS_Store', 'Thumbs.db'
        }
        
        logger.info(f"🔍 ProjectAwareFileHandler initialized")
        logger.info(f"📁 Workspace root: {self.workspace_root}")
        logger.info(f"⏱️ Debounce delay: {self.debounce_delay}s")
        logger.info(f"📄 Monitoring {len(self.monitored_extensions)} file types")
    
    def _default_user_id_extractor(self, file_path: str) -> str:
        """
        Default user ID extractor. Can be overridden for custom logic.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            User ID (defaults to 'default_user')
        """
        # In a real implementation, this might extract user info from:
        # - Path structure (e.g., /workspace/users/alice/project_a/file.py)
        # - Environment variables
        # - Configuration files
        # - Git authorship
        return "default_user"
    
    def _extract_project_context(self, file_path: str) -> Optional[tuple[str, str]]:
        """
        Extract project_id and user_id from the file path.
        
        Args:
            file_path: Full path to the changed file
            
        Returns:
            Tuple of (user_id, project_id) or None if extraction fails
        """
        try:
            file_path_obj = Path(file_path).resolve()
            
            # Check if file is within workspace
            if not str(file_path_obj).startswith(str(self.workspace_root)):
                return None
            
            # Get relative path from workspace root
            relative_path = file_path_obj.relative_to(self.workspace_root)
            path_parts = relative_path.parts
            
            if len(path_parts) < 2:  # Need at least project_dir/file
                return None
            
            # Extract project_id from first directory level
            project_id = path_parts[0]
            
            # Check if any excluded directory is in the path
            if any(excluded in path_parts for excluded in self.excluded_dirs):
                return None
            
            # Extract user_id (could be from path or other logic)
            user_id = self.user_id_extractor(file_path)
            
            return user_id, project_id
            
        except Exception as e:
            logger.warning(f"Failed to extract project context from {file_path}: {e}")
            return None
    
    def _should_monitor_file(self, file_path: str) -> bool:
        """
        Determine if a file should be monitored based on extension and location.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be monitored
        """
        file_path_obj = Path(file_path)
        
        # Check file extension
        if file_path_obj.suffix.lower() not in self.monitored_extensions:
            return False
        
        # Check if in excluded directory
        if any(excluded in file_path_obj.parts for excluded in self.excluded_dirs):
            return False
        
        # Check file size (skip very large files)
        try:
            if file_path_obj.exists() and file_path_obj.stat().st_size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Skipping large file: {file_path} ({file_path_obj.stat().st_size} bytes)")
                return False
        except OSError:
            pass
        
        return True
    
    def _create_file_event(self, event: FileSystemEvent, event_type: str) -> Optional[FileChangeEvent]:
        """
        Create a FileChangeEvent from a watchdog event.
        
        Args:
            event: Watchdog file system event
            event_type: Type of event ('created', 'modified', 'deleted', 'moved')
            
        Returns:
            FileChangeEvent or None if event should be ignored
        """
        file_path = event.src_path
        
        # Skip if not a file we should monitor
        if not self._should_monitor_file(file_path):
            return None
        
        # Extract project context
        context = self._extract_project_context(file_path)
        if not context:
            return None
        
        user_id, project_id = context
        
        # Create event
        file_event = FileChangeEvent(
            file_path=file_path,
            project_id=project_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=time.time()
        )
        
        # Handle move events
        if hasattr(event, 'dest_path') and event.dest_path:
            file_event.src_path = event.src_path
            file_event.dest_path = event.dest_path
        
        return file_event
    
    def _schedule_processing(self, file_event: FileChangeEvent):
        """
        Schedule processing of a file event with debouncing.
        
        Args:
            file_event: The file change event to process
        """
        file_path = file_event.file_path
        
        # Cancel existing timer for this file
        if file_path in self.debounce_timers:
            self.debounce_timers[file_path].cancel()
        
        # Store the latest event (this replaces any previous pending event)
        self.pending_events[file_path] = file_event
        
        # Schedule processing after debounce delay
        timer = Timer(self.debounce_delay, self._process_file_event, args=[file_path])
        self.debounce_timers[file_path] = timer
        timer.start()
        
        logger.debug(f"📅 Scheduled processing for {file_path} (project: {file_event.project_id})")
    
    def _process_file_event(self, file_path: str):
        """
        Process a debounced file event by updating the project's MemCube.
        
        Args:
            file_path: Path to the file that changed
        """
        try:
            # Get the pending event
            if file_path not in self.pending_events:
                return
            
            file_event = self.pending_events.pop(file_path)
            
            # Clean up timer
            if file_path in self.debounce_timers:
                del self.debounce_timers[file_path]
            
            logger.info(f"🔄 Processing {file_event.event_type} event: {file_path}")
            logger.info(f"📊 Project: {file_event.project_id}, User: {file_event.user_id}")
            
            # Process the event based on type
            if file_event.event_type in ['created', 'modified']:
                self._ingest_file_to_project(file_event)
            elif file_event.event_type == 'deleted':
                self._remove_file_from_project(file_event)
            elif file_event.event_type == 'moved':
                self._handle_file_move(file_event)
            
        except Exception as e:
            logger.error(f"❌ Error processing file event for {file_path}: {e}")
    
    def _ingest_file_to_project(self, file_event: FileChangeEvent):
        """
        Ingest a file into the specific project's MemCube.
        
        Args:
            file_event: The file change event containing project context
        """
        try:
            file_path = Path(file_event.file_path)
            
            # Check if file still exists
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path}")
                return
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return
            
            # Skip empty files
            if not content.strip():
                logger.debug(f"Skipping empty file: {file_path}")
                return
            
            # Prepare memory content with metadata
            try:
                relative_path = file_path.relative_to(self.workspace_root)
            except ValueError:
                # Handle case where paths are resolved differently (e.g., symlinks on macOS)
                workspace_resolved = self.workspace_root.resolve()
                file_resolved = file_path.resolve()
                try:
                    relative_path = file_resolved.relative_to(workspace_resolved)
                except ValueError:
                    # Last resort - string manipulation
                    workspace_str = str(workspace_resolved)
                    file_str = str(file_resolved)
                    if file_str.startswith(workspace_str):
                        relative_path = Path(file_str[len(workspace_str):].lstrip('/'))
                    else:
                        logger.warning(f"File {file_path} not in workspace {self.workspace_root}")
                        return
            
            memory_content = f"""File: {relative_path}
Project: {file_event.project_id}
Last Modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_event.timestamp))}

{content}"""
            
            # Add to project memory
            success = self.project_memory_manager.add_memory_to_project(
                user_id=file_event.user_id,
                project_id=file_event.project_id,
                memory_content=memory_content,
                metadata={
                    'file_path': str(relative_path),
                    'absolute_path': str(file_path),
                    'event_type': file_event.event_type,
                    'timestamp': file_event.timestamp,
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix
                }
            )
            
            if success:
                logger.info(f"✅ Ingested {relative_path} to project {file_event.project_id}")
            else:
                logger.warning(f"⚠️ Failed to ingest {relative_path} to project {file_event.project_id}")
                
        except Exception as e:
            logger.error(f"❌ Error ingesting file {file_event.file_path}: {e}")
    
    def _remove_file_from_project(self, file_event: FileChangeEvent):
        """
        Remove a file's memory from the specific project's MemCube.
        
        Args:
            file_event: The file deletion event
        """
        try:
            file_path = Path(file_event.file_path)
            try:
                relative_path = file_path.relative_to(self.workspace_root)
            except ValueError:
                # Handle case where paths are resolved differently (e.g., symlinks on macOS)
                workspace_resolved = self.workspace_root.resolve()
                file_resolved = file_path.resolve()
                try:
                    relative_path = file_resolved.relative_to(workspace_resolved)
                except ValueError:
                    # Last resort - string manipulation
                    workspace_str = str(workspace_resolved)
                    file_str = str(file_resolved)
                    if file_str.startswith(workspace_str):
                        relative_path = Path(file_str[len(workspace_str):].lstrip('/'))
                    else:
                        logger.warning(f"File {file_path} not in workspace {self.workspace_root}")
                        return
            
            # Search for memories related to this file
            search_result = self.project_memory_manager.search_project_memory(
                user_id=file_event.user_id,
                project_id=file_event.project_id,
                query=f"File: {relative_path}",
                top_k=5
            )
            
            if search_result and search_result.get('results'):
                logger.info(f"🗑️ Found {len(search_result['results'])} memories for deleted file {relative_path}")
                # Note: Actual memory deletion would require additional MemOS API calls
                # For now, we log the detection
            else:
                logger.debug(f"No memories found for deleted file {relative_path}")
                
        except Exception as e:
            logger.error(f"❌ Error removing file memory {file_event.file_path}: {e}")
    
    def _handle_file_move(self, file_event: FileChangeEvent):
        """
        Handle file move/rename events.
        
        Args:
            file_event: The file move event
        """
        try:
            if file_event.src_path and file_event.dest_path:
                logger.info(f"📁 File moved: {file_event.src_path} → {file_event.dest_path}")
                
                # For moves, we treat it as a delete + create
                # First remove the old file memory
                old_event = FileChangeEvent(
                    file_path=file_event.src_path,
                    project_id=file_event.project_id,
                    user_id=file_event.user_id,
                    event_type='deleted',
                    timestamp=file_event.timestamp
                )
                self._remove_file_from_project(old_event)
                
                # Then add the new file
                new_event = FileChangeEvent(
                    file_path=file_event.dest_path,
                    project_id=file_event.project_id,
                    user_id=file_event.user_id,
                    event_type='created',
                    timestamp=file_event.timestamp
                )
                self._ingest_file_to_project(new_event)
                
        except Exception as e:
            logger.error(f"❌ Error handling file move: {e}")
    
    # Watchdog event handlers
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            file_event = self._create_file_event(event, 'created')
            if file_event:
                self._schedule_processing(file_event)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            file_event = self._create_file_event(event, 'modified')
            if file_event:
                self._schedule_processing(file_event)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            file_event = self._create_file_event(event, 'deleted')
            if file_event:
                self._schedule_processing(file_event)
    
    def on_moved(self, event):
        """Handle file move/rename events."""
        if not event.is_directory:
            file_event = self._create_file_event(event, 'moved')
            if file_event:
                self._schedule_processing(file_event)


class ProjectAwareFileMonitor:
    """
    Main class for managing project-aware file monitoring.
    
    This class orchestrates the file watching system, manages observers,
    and coordinates with the MemCube lifecycle system.
    """
    
    def __init__(
        self,
        workspace_root: str,
        project_memory_manager: ProjectMemoryManager,
        debounce_delay: float = 0.5,
        user_id_extractor: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize the project-aware file monitor.
        
        Args:
            workspace_root: Root directory containing project subdirectories
            project_memory_manager: Instance for managing project memories
            debounce_delay: Delay in seconds for debouncing rapid changes
            user_id_extractor: Function to extract user_id from paths
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog package is required for file monitoring")
        
        self.workspace_root = Path(workspace_root).resolve()
        self.project_memory_manager = project_memory_manager
        self.debounce_delay = debounce_delay
        
        # Create event handler
        self.event_handler = ProjectAwareFileHandler(
            workspace_root=str(self.workspace_root),
            project_memory_manager=project_memory_manager,
            debounce_delay=debounce_delay,
            user_id_extractor=user_id_extractor
        )
        
        # File system observer
        self.observer = Observer()
        self.is_monitoring = False
        
        logger.info(f"🔍 ProjectAwareFileMonitor initialized for {self.workspace_root}")
    
    def start_monitoring(self, recursive: bool = True):
        """
        Start monitoring the workspace directory.
        
        Args:
            recursive: Whether to monitor subdirectories recursively
        """
        if self.is_monitoring:
            logger.warning("File monitoring is already active")
            return
        
        try:
            # Ensure workspace directory exists
            self.workspace_root.mkdir(parents=True, exist_ok=True)
            
            # Schedule the event handler
            self.observer.schedule(
                self.event_handler,
                str(self.workspace_root),
                recursive=recursive
            )
            
            # Start the observer
            self.observer.start()
            self.is_monitoring = True
            
            logger.info(f"🚀 Started monitoring {self.workspace_root}")
            logger.info(f"📁 Recursive monitoring: {recursive}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start file monitoring: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop monitoring the workspace directory."""
        if not self.is_monitoring:
            return
        
        try:
            self.observer.stop()
            self.observer.join(timeout=5.0)  # Wait up to 5 seconds
            self.is_monitoring = False
            
            logger.info("🛑 Stopped file monitoring")
            
        except Exception as e:
            logger.error(f"❌ Error stopping file monitoring: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status and statistics.
        
        Returns:
            Dictionary with monitoring information
        """
        return {
            'is_monitoring': self.is_monitoring,
            'workspace_root': str(self.workspace_root),
            'debounce_delay': self.debounce_delay,
            'pending_events': len(self.event_handler.pending_events),
            'active_timers': len(self.event_handler.debounce_timers),
            'monitored_extensions': list(self.event_handler.monitored_extensions),
            'excluded_dirs': list(self.event_handler.excluded_dirs)
        }
    
    def force_sync_project(self, project_id: str, user_id: str = "default_user"):
        """
        Force a complete sync of a specific project.
        
        Args:
            project_id: Project identifier to sync
            user_id: User identifier
        """
        try:
            project_dir = self.workspace_root / project_id
            
            if not project_dir.exists():
                logger.warning(f"Project directory not found: {project_dir}")
                return
            
            logger.info(f"🔄 Force syncing project: {project_id}")
            
            # Walk through all files in the project
            for file_path in project_dir.rglob('*'):
                if file_path.is_file() and self.event_handler._should_monitor_file(str(file_path)):
                    # Create a synthetic file event
                    file_event = FileChangeEvent(
                        file_path=str(file_path),
                        project_id=project_id,
                        user_id=user_id,
                        event_type='modified',
                        timestamp=time.time()
                    )
                    
                    # Process immediately (bypass debouncing for force sync)
                    self.event_handler._ingest_file_to_project(file_event)
            
            logger.info(f"✅ Force sync completed for project: {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error during force sync of project {project_id}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()


# Utility functions for integration
def create_workspace_structure(workspace_root: str, projects: list[str]):
    """
    Create a workspace directory structure for testing.
    
    Args:
        workspace_root: Root workspace directory
        projects: List of project names to create
    """
    workspace_path = Path(workspace_root)
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    for project in projects:
        project_dir = workspace_path / project
        project_dir.mkdir(exist_ok=True)
        
        # Create sample subdirectories
        (project_dir / "src").mkdir(exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)
        (project_dir / "docs").mkdir(exist_ok=True)
    
    logger.info(f"📁 Created workspace structure with {len(projects)} projects")


# Example usage and testing
if __name__ == "__main__":
    print("🔍 Project-Aware File Monitor - Test Mode")
    print("=" * 50)
    
    if not WATCHDOG_AVAILABLE:
        print("❌ watchdog package not available")
        print("💡 Install with: pip install watchdog")
        sys.exit(1)
    
    if not MEMOS_AVAILABLE:
        print("⚠️ MemOS not available - using mock mode")
    
    # Create test workspace
    test_workspace = "./test_workspace"
    test_projects = ["project_alpha", "project_beta", "project_gamma"]
    
    create_workspace_structure(test_workspace, test_projects)
    
    # Initialize project memory manager
    pm_manager = ProjectMemoryManager()
    
    # Create and start monitor
    try:
        monitor = ProjectAwareFileMonitor(
            workspace_root=test_workspace,
            project_memory_manager=pm_manager,
            debounce_delay=0.5
        )
        
        print(f"📊 Monitor status: {monitor.get_monitoring_status()}")
        
        # In a real application, you would start monitoring and let it run
        # monitor.start_monitoring()
        # ... application continues ...
        # monitor.stop_monitoring()
        
        print("✅ Project-Aware File Monitor initialized successfully!")
        print("💡 Start monitoring with monitor.start_monitoring()")
        
    except Exception as e:
        print(f"❌ Error initializing monitor: {e}")