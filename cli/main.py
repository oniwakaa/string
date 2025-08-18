#!/usr/bin/env python3
"""
String CLI - A local AI coding assistant powered by multi-agent architecture.

This CLI serves as the primary interface to the validated backend system
that includes intelligent codebase loading, multi-agent orchestration,
and MemOS RAG integration.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Prompt, Confirm
from urllib.parse import urlparse

# Import health check functionality
from cli.runtime_health import run_runtime_checks, DependencyError
# Import runtime home management
from cli.runtime_home import ensure_string_home, get_string_home, initialize_default_configs
# Import backend management
from cli.backend_manager import get_backend_manager


app = typer.Typer(
    name="string-cli",
    help="Local AI coding assistant with multi-agent capabilities",
    add_completion=False,
    rich_markup_mode="rich"
)

console = Console()

# Backend configuration (resolved dynamically from backend_manager when needed)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Session state for interactive mode
class SessionState:
    """Manages state for the interactive session."""
    def __init__(self):
        self.project_id: Optional[str] = None
        self.project_path: Optional[Path] = None
        self.backend_started_by_session: bool = False
        self.codebase_loaded: bool = False
        
    def reset(self):
        """Clear session-local state (not STRING_HOME assets)."""
        self.project_id = None
        self.codebase_loaded = False
        # Keep project_path and backend ownership

session_state = SessionState()


def _count_candidate_files(directory: Path, threshold: int = 10000) -> tuple[int, bool]:
    """
    Count files that would be processed, respecting .memignore if present.
    Uses similar filtering logic as the backend would use.
    
    Returns:
        tuple: (file_count, has_memignore)
    """
    memignore_path = directory / '.memignore'
    has_memignore = memignore_path.exists()
    
    # Load .memignore patterns if available
    ignore_patterns = []
    if has_memignore:
        try:
            with open(memignore_path, 'r') as f:
                ignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception:
            pass
    
    # Default ignore patterns (similar to what backend uses)
    default_ignores = {'.git', '__pycache__', 'node_modules', '.DS_Store', '*.pyc', '*.log', '.env'}
    
    # Code file extensions (similar to what backend processes)
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', 
                      '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj', 
                      '.sql', '.html', '.css', '.scss', '.less', '.md', '.txt', '.json', '.yaml', '.yml',
                      '.xml', '.toml', '.ini', '.cfg', '.conf'}
    
    count = 0
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)
            
            for item in directory.rglob('*'):
                if count > threshold:  # Early exit for performance
                    break
                    
                if not item.is_file():
                    continue
                
                # Check if file should be ignored
                relative_path = item.relative_to(directory)
                
                # Skip hidden files and directories
                if any(part.startswith('.') for part in relative_path.parts):
                    continue
                
                # Skip if matches ignore patterns
                path_str = str(relative_path)
                if any(pattern in path_str or relative_path.match(pattern) for pattern in ignore_patterns):
                    continue
                
                # Skip if matches default ignores
                if any(ignore in path_str for ignore in default_ignores):
                    continue
                    
                # Only count files with code extensions
                if item.suffix.lower() in code_extensions:
                    count += 1
                    
                # Update progress occasionally
                if count % 1000 == 0:
                    progress.update(task, description=f"Scanning files... {count:,} found")
                    
            progress.update(task, description=f"File scan complete: {count:,} files")
            
    except (PermissionError, OSError) as e:
        console.print(f"⚠️  [yellow]Warning during file scan:[/yellow] {e}")
    
    return count, has_memignore


def _prompt_for_load_confirmation(directory: Path) -> bool:
    """
    Prompt user for codebase loading confirmation with .memignore warning if needed.
    
    Returns:
        bool: True if user wants to proceed with loading
    """
    file_count, has_memignore = _count_candidate_files(directory)
    
    if file_count > 10000 and not has_memignore:
        console.print(f"\n⚠️  [yellow]Warning:[/yellow] This repository has {file_count:,}+ files and no .memignore file.")
        console.print("Loading everything may be slow and consume significant memory.")
        console.print("\n💡 [cyan]Consider creating a .memignore file with patterns like:[/cyan]")
        console.print("   node_modules/")
        console.print("   .git/")
        console.print("   __pycache__/")
        console.print("   *.log")
        
        return Confirm.ask("\nLoad all files anyway?", default=False)
    
    return Confirm.ask(f"\nLoad this codebase ({file_count:,} files)?", default=True)

def _make_api_endpoints(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, str]:
    base = f"http://{host}:{port}"
    return {
        "health": f"{base}/health",
        "chat": f"{base}/chat",
        "load_codebase": f"{base}/load_codebase",
        "execute_task": f"{base}/execute_agentic_task",
        "clear": f"{base}/clear",
        "compact": f"{base}/compact",
    }


class BackendClient:
    """HTTP client for communicating with the GGUF memory service backend."""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.api = _make_api_endpoints(host, port)
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> Dict[str, Any]:
        """Check if the backend service is running and healthy."""
        try:
            response = await self.client.get(self.api["health"])
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Backend service unavailable: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Backend health check failed: {e}")
    
    async def load_codebase(self, path: str, show_progress: bool = True) -> Dict[str, Any]:
        """Load codebase into the backend memory system with progress tracking."""
        try:
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=False
                ) as progress:
                    task = progress.add_task(f"Loading codebase from {Path(path).name}...", total=100)
                    
                    response = await self.client.post(
                        self.api["load_codebase"],
                        json={"directory_path": path}
                    )
                    progress.update(task, completed=100, description="Codebase loaded successfully!")
                    response.raise_for_status()
                    return response.json()
            else:
                response = await self.client.post(
                    self.api["load_codebase"],
                    json={"directory_path": path}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Failed to load codebase: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Codebase loading failed: {e}")
    
    async def execute_task(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an agentic task through the multi-agent orchestrator."""
        try:
            payload = {
                "prompt": prompt,
                "user_id": (context or {}).get("user_id", "default_user"),
                "project_id": (context or {}).get("project_id", "default"),
            }
            
            response = await self.client.post(
                self.api["execute_task"],
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Task execution failed: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Task execution error: {e}")
    
    async def clear_workspace(self, workspace_id: str = "default") -> Dict[str, Any]:
        """Clear workspace context."""
        try:
            response = await self.client.post(
                self.api["clear"],
                json={"workspace_id": workspace_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Clear operation failed: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Clear operation error: {e}")
    
    async def compact_workspace(self, workspace_id: str = "default") -> Dict[str, Any]:
        """Compact workspace context."""
        try:
            response = await self.client.post(
                self.api["compact"],
                json={"workspace_id": workspace_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Compact operation failed: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Compact operation error: {e}")
    
    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()


async def _handle_session_status(client: BackendClient):
    """Handle /status session command."""
    try:
        health = await client.check_health()
        
        # Create comprehensive status display
        table = Table(title="System Status", show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")
        
        # Backend service
        backend_manager = get_backend_manager()
        status_info = backend_manager.get_backend_status()
        service_status = "🟢 Running" if status_info['healthy'] else "🔴 Unhealthy"
        table.add_row("Backend", service_status, f"{status_info['url']}")
        
        # Service initialization
        service = health.get('service', {})
        init_status = "✅ Yes" if service.get('initialized') else "❌ No"
        error_detail = service.get('error') or "None"
        table.add_row("Initialized", init_status, error_detail)
        
        # Model status
        model = health.get('model', {})
        model_status = "✅ Loaded" if model.get('loaded') else "❌ Not loaded"
        model_name = model.get('info', {}).get('model_name', 'Unknown')
        table.add_row("Model", model_status, f"{model_name}")
        
        # Memory system
        memos = health.get('memos', {})
        memos_status = f"🟢 {memos.get('status', 'unknown')}"
        cubes_count = memos.get('cubes_count', 0)
        table.add_row("MemOS", memos_status, f"{cubes_count} cubes")
        
        # Storage paths
        string_home = get_string_home()
        table.add_row("Storage", "📁 Ready", f"{string_home}")
        
        console.print(table)
        
        # Session info
        console.print(f"\n📂 [blue]Current Directory:[/blue] {Path.cwd()}")
        if session_state.project_path:
            console.print(f"🔗 [blue]Bound Project:[/blue] {session_state.project_path}")
        if session_state.project_id:
            console.print(f"🆔 [blue]Project ID:[/blue] {session_state.project_id}")
        
    except Exception as e:
        console.print(f"❌ [red]Status check failed:[/red] {e}")


async def _handle_session_clear(client: BackendClient):
    """Handle /clear session command."""
    try:
        result = await client.clear_workspace()
        session_state.reset()
        
        console.print(Panel.fit(
            "✅ [green]Session context cleared[/green]\n"
            "• Local session state reset\n"
            "• Backend workspace cleared\n" 
            "• STRING_HOME assets preserved",
            title="Clear Complete",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"❌ [red]Clear operation failed:[/red] {e}")


async def _handle_session_compact(client: BackendClient):
    """Handle /compact session command."""
    try:
        result = await client.compact_workspace()
        
        if result.get("success", False):
            console.print(Panel.fit(
                f"✅ [green]Workspace compacted[/green]\n"
                f"Original: {result.get('original_length', 0)} tokens\n"
                f"Compressed: {result.get('compressed_length', 0)} tokens",
                title="Compact Complete",
                border_style="green"
            ))
        else:
            console.print("ℹ️  [yellow]Compaction not supported by backend[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Compact operation failed:[/red] {e}")


async def _ensure_codebase_loaded(client: BackendClient, directory: Path) -> bool:
    """
    Ensure codebase is loaded with user confirmation and progress display.
    Blocks all user interaction until loading is complete or explicitly skipped.
    
    Returns:
        bool: True if codebase is loaded or user skipped, False if user cancelled
    """
    if session_state.codebase_loaded:
        return True
    
    # Step 1: Pre-load file count and confirmation
    console.print("\n🔍 [blue]Analyzing codebase...[/blue]")
    
    if not _prompt_for_load_confirmation(directory):
        skip_confirm = Confirm.ask("\nSkip codebase loading? (responses will not be memory-enhanced)", default=False)
        if skip_confirm:
            console.print("ℹ️  [yellow]Codebase loading skipped. Responses will not be memory-enhanced.[/yellow]")
            return True
        else:
            return False
    
    # Step 2: Start loading with blocking progress bar
    console.print("\n🚀 [green]Starting codebase loading...[/green]")
    console.print("⚠️  [yellow]Please wait - user input blocked until loading completes.[/yellow]\n")
    
    loading_complete = False
    loading_error = None
    result = None
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            # Create progress task
            load_task = progress.add_task("Loading codebase files...", total=100)
            
            # Start the loading operation
            progress.update(load_task, completed=10, description="Initializing loader...")
            
            # Start the actual backend call
            async def perform_load():
                nonlocal result, loading_error, loading_complete
                try:
                    result = await client.load_codebase(str(directory), show_progress=False)
                    loading_complete = True
                except Exception as e:
                    loading_error = str(e)
                    loading_complete = True
            
            # Start loading task
            load_future = asyncio.create_task(perform_load())
            
            # Simulate progress with polling (since we don't have streaming)
            progress_value = 10
            while not loading_complete:
                await asyncio.sleep(1.0)  # Poll every second
                
                # Gradually increase progress
                if progress_value < 90:
                    progress_value = min(90, progress_value + 5)
                    
                    if progress_value < 30:
                        desc = "Processing files..."
                    elif progress_value < 60:
                        desc = "Extracting code content..."
                    elif progress_value < 80:
                        desc = "Generating embeddings..."
                    else:
                        desc = "Storing in vector database..."
                        
                    progress.update(load_task, completed=progress_value, description=desc)
            
            # Wait for the load operation to complete
            await load_future
            
            # Complete the progress bar
            if loading_error:
                progress.update(load_task, completed=100, description="❌ Loading failed!")
            else:
                progress.update(load_task, completed=100, description="✅ Loading completed!")
        
        # Handle results
        if loading_error:
            console.print(f"\n❌ [red]Failed to load codebase:[/red] {loading_error}")
            return False
        
        if result:
            # Update session state
            session_state.project_path = directory
            session_state.project_id = result.get('project_id', str(directory.name))
            session_state.codebase_loaded = True
            
            # Display results
            files_loaded = result.get('files_loaded', 0)
            files_failed = result.get('files_failed', 0)
            collection_name = result.get('collection_name', 'unknown')
            
            console.print(Panel.fit(
                f"✅ [green]Codebase loaded successfully![/green]\n"
                f"Files processed: {files_loaded:,}\n"
                f"Files failed: {files_failed:,}\n"
                f"Project ID: {session_state.project_id}\n"
                f"Collection: {collection_name}\n"
                f"Storage: {get_string_home()}/storage\n\n"
                f"💡 [cyan]Ready for memory-enhanced AI assistance![/cyan]",
                title="Loading Complete",
                border_style="green"
            ))
            
            console.print("\n🎯 [blue]You can now ask questions about your codebase![/blue]")
            return True
        
    except Exception as e:
        console.print(f"\n❌ [red]Unexpected error during loading:[/red] {e}")
        return False


async def _run_interactive_session():
    """
    Run the persistent interactive session (REPL mode).
    """
    console.print(Panel.fit(
        f"🚀 [green]String CLI Interactive Session[/green]\n"
        f"📂 Project: {Path.cwd()}\n"
        f"🏠 Runtime: {get_string_home()}\n\n"
        f"Commands: /status, /clear, /compact, /quit\n"
        f"Type naturally for AI assistance.",
        title="Welcome",
        border_style="blue"
    ))
    
    client = BackendClient()
    current_dir = Path.cwd()
    
    try:
        # Check if backend is already running (avoid double startup)
        backend_manager = get_backend_manager()
        is_running, _ = backend_manager.is_backend_running()
        
        if not is_running:
            # Only start if not already running
            if not await backend_manager.ensure_backend_running():
                console.print("❌ [red]Failed to start backend. Interactive session cannot continue.[/red]")
                return
            session_state.backend_started_by_session = True
        else:
            console.print("🔄 Using existing backend instance...")
        
        # Check initial backend health and display any errors
        try:
            health = await client.check_health()
            service_error = health.get('service', {}).get('error')
            if service_error:
                console.print(f"⚠️  [yellow]Backend started with warning:[/yellow] {service_error}")
        except Exception as e:
            console.print(f"⚠️  [yellow]Backend health check failed:[/yellow] {e}")
        
        # Try to ensure codebase is loaded
        if not await _ensure_codebase_loaded(client, current_dir):
            console.print("❌ [red]Session cancelled by user[/red]")
            return
        
        # Main REPL loop
        while True:
            try:
                # Show current context in prompt
                project_name = session_state.project_path.name if session_state.project_path else current_dir.name
                prompt_text = f"[{project_name}]> "
                
                user_input = Prompt.ask(prompt_text).strip()
                
                if not user_input:
                    continue
                
                # Handle session commands
                if user_input == "/quit":
                    console.print("👋 [blue]Goodbye![/blue]")
                    break
                elif user_input == "/status":
                    await _handle_session_status(client)
                elif user_input == "/clear":
                    await _handle_session_clear(client)
                elif user_input == "/compact":
                    await _handle_session_compact(client)
                else:
                    # Handle natural language prompt
                    await _handle_natural_language_prompt(client, user_input)
                
            except KeyboardInterrupt:
                console.print("\n👋 [blue]Goodbye![/blue]")
                break
            except EOFError:
                console.print("\n👋 [blue]Goodbye![/blue]")
                break
            except Exception as e:
                console.print(f"❌ [red]Session error:[/red] {e}")
    
    finally:
        # Clean shutdown
        await client.close()
        
        # Stop backend if we started it
        if session_state.backend_started_by_session:
            backend_manager = get_backend_manager()
            is_running, pid = backend_manager.is_backend_running()
            if is_running:
                console.print("🛑 [dim]Stopping backend...[/dim]")
                backend_manager.stop_backend(pid)


@app.command()
def validate():
    """Run comprehensive runtime dependency validation checks."""
    try:
        run_runtime_checks(verbose=True)
        
        console.print("\n🎉 [green]All runtime validation checks passed![/green]")
        console.print("✅ [green]String CLI is ready for use[/green]")
        
    except DependencyError as e:
        console.print(f"\n❌ [red]Runtime validation failed:[/red] {e.message}")
        if e.suggestions:
            console.print("\n💡 [cyan]Suggested fixes:[/cyan]")
            for suggestion in e.suggestions:
                console.print(f"   • {suggestion}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n⚠️  [yellow]Runtime validation error:[/yellow] {e}")
        raise typer.Exit(code=1)


@app.command()
def cli_status():
    """Show backend service and CLI status."""
    backend_manager = get_backend_manager()
    status_info = backend_manager.get_backend_status()
    console.print("🔍 [blue]String CLI Status[/blue]")
    console.print(f"Runtime home: {get_string_home()}")
    if status_info['running']:
        status_color = "green" if status_info['healthy'] else "yellow"
        health_text = "Healthy" if status_info['healthy'] else "Unhealthy"
        console.print(f"Backend: [{status_color}]{health_text}[/{status_color}] (PID: {status_info['pid']})")
    else:
        console.print("Backend: [red]Not Running[/red]")
    console.print(f"Backend URL: {status_info['url']}")
    if status_info['log_file']:
        console.print(f"Log file: {status_info['log_file']}")


@app.command()
def start_backend():
    """Manually start the backend service."""
    backend_manager = get_backend_manager()
    is_running, pid = backend_manager.is_backend_running()
    if is_running:
        console.print(f"✅ [green]Backend already running[/green] (PID: {pid})")
        return
    console.print("🚀 Starting backend service...")
    success, pid = backend_manager.start_backend()
    if success:
        console.print(f"✅ [green]Backend started successfully[/green] (PID: {pid})")
    else:
        console.print("❌ [red]Failed to start backend service[/red]")
        raise typer.Exit(code=1)


@app.command()
def stop_backend():
    """Stop the backend service."""
    backend_manager = get_backend_manager()
    
    is_running, pid = backend_manager.is_backend_running()
    if not is_running:
        console.print("✅ [green]Backend is not running[/green]")
        return
    
    console.print(f"🛑 Stopping backend service (PID: {pid})...")
    success = backend_manager.stop_backend(pid)
    
    if success:
        console.print("✅ [green]Backend stopped successfully[/green]")
    else:
        console.print("❌ [red]Failed to stop backend service[/red]")
        raise typer.Exit(code=1)


# Unified command handler - replaces individual commands
@app.command()
def execute(
    user_input: str = typer.Argument(
        ..., 
        help="Natural language prompt or special command (/clear, /compact)"
    )
):
    """Execute user input - natural language prompts or special commands."""
    
    async def _execute():
        client = BackendClient()
        try:
            # Check backend health first
            await client.check_health()
            
            # Route input based on content
            if user_input.strip() == "/clear":
                await _handle_clear_command(client)
            elif user_input.strip() == "/compact":
                await _handle_compact_command(client)
            else:
                await _handle_natural_language_prompt(client, user_input)
                
        finally:
            await client.close()
    
    asyncio.run(_execute())


async def _handle_clear_command(client: BackendClient):
    """Handle /clear special command."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Clearing workspace context...", total=None)
        result = await client.clear_workspace()
        progress.update(task, description="Clear operation completed!")
    
    if result.get("success", False):
        console.print(Panel.fit(
            f"✅ [green]Context cleared successfully[/green]\n"
            f"Workspace: {result.get('workspace_id', 'default')}\n"
            f"Cleared: {', '.join(result.get('cleared_components', []))}",
            title="Clear Complete",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"❌ [red]Clear operation failed[/red]\n"
            f"Message: {result.get('message', 'Unknown error')}",
            title="Clear Failed",
            border_style="red"
        ))


async def _handle_compact_command(client: BackendClient):
    """Handle /compact special command."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Compacting workspace context...", total=None)
        result = await client.compact_workspace()
        progress.update(task, description="Compact operation completed!")
    
    if result.get("success", False):
        console.print(Panel.fit(
            f"✅ [green]Context compacted successfully[/green]\n"
            f"Workspace: {result.get('workspace_id', 'default')}\n"
            f"Compressed: {result.get('original_length', 0)} → {result.get('compressed_length', 0)} tokens",
            title="Compact Complete",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"❌ [red]Compact operation failed[/red]\n"
            f"Message: {result.get('message', 'Unknown error')}",
            title="Compact Failed",
            border_style="red"
        ))


async def _handle_natural_language_prompt(client: BackendClient, prompt: str):
    """Handle natural language prompt with streaming output."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Processing your request...", total=None)
        result = await client.execute_task(prompt)
        progress.update(task, description="Task completed!")
    
    # Display execution summary
    console.print(Panel.fit(
        f"🤖 [blue]Status:[/blue] {result.get('status', 'unknown')}\n"
        f"Message: {result.get('message', 'No message')}",
        title="Execution Summary", 
        border_style="blue"
    ))
    
    # Show response/result
    response_content = result.get('result', result.get('response', 'No response available'))
    console.print(Panel(
        str(response_content),
        title="Agent Response",
        border_style="cyan"
    ))


@app.command()
def health():
    """Check the health status of the backend service."""
    async def _health():
        client = BackendClient()
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                progress.add_task("Checking backend health...", total=None)
                status = await client.check_health()
            
            console.print(Panel.fit(
                f"✅ Backend service status: [green]{status.get('status', 'unknown')}[/green]\n"
                f"Service: {status.get('service', {}).get('name', 'Unknown')}\n"
                f"Model loaded: {status.get('model', {}).get('loaded', False)}",
                title="Backend Health",
                border_style="green"
            ))
        finally:
            await client.close()
    
    asyncio.run(_health())


@app.command()
def load(
    path: str = typer.Argument(
        ..., 
        help="Path to the codebase directory to load"
    ),
    force: bool = typer.Option(
        False, 
        "--force", 
        "-f", 
        help="Force reload even if codebase is already loaded"
    )
):
    """Load a codebase into the intelligent memory system."""
    async def _load():
        client = BackendClient()
        try:
            # Validate path exists
            codebase_path = Path(path).resolve()
            if not codebase_path.exists():
                console.print(f"❌ [red]Path does not exist:[/red] {codebase_path}")
                raise typer.Exit(1)
            
            if not codebase_path.is_dir():
                console.print(f"❌ [red]Path is not a directory:[/red] {codebase_path}")
                raise typer.Exit(1)
            
            # Check backend health first
            await client.check_health()
            
            # Load codebase
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                progress.add_task(f"Loading codebase from {codebase_path}...", total=None)
                result = await client.load_codebase(str(codebase_path))
            
            # Display results
            files_loaded = result.get('files_loaded', 0)
            context_size = result.get('context_size', 'unknown')
            memory_usage = result.get('memory_usage', 'unknown')
            
            console.print(Panel.fit(
                f"✅ [green]Codebase loaded successfully[/green]\n"
                f"Files processed: {files_loaded}\n"
                f"Context size: {context_size}\n"
                f"Memory usage: {memory_usage}",
                title="Codebase Loading Complete",
                border_style="green"
            ))
        finally:
            await client.close()
    
    asyncio.run(_load())


@app.command()
def ask(
    prompt: str = typer.Argument(
        ..., 
        help="Natural language prompt describing the coding task"
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-c",
        help="Additional context as JSON string"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v", 
        help="Show detailed execution information"
    )
):
    """Execute a natural language coding task using multi-agent orchestration."""
    async def _ask():
        client = BackendClient()
        try:
            # Parse context if provided
            context_dict = None
            if context:
                try:
                    context_dict = json.loads(context)
                except json.JSONDecodeError:
                    console.print(f"❌ [red]Invalid JSON context:[/red] {context}")
                    raise typer.Exit(1)
            
            # Check backend health
            await client.check_health()
            
            # Execute task
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Processing your request...", total=None)
                result = await client.execute_task(prompt, context_dict)
                progress.update(task, description="Task completed!")
            
            # Display results
            console.print(Panel.fit(
                f"🤖 [blue]Task Status:[/blue] {result.get('status', 'unknown')}\n"
                f"Agent Used: {result.get('agent', 'unknown')}\n"
                f"Execution Time: {result.get('execution_time', 'unknown')}s",
                title="Execution Summary", 
                border_style="blue"
            ))
            
            # Show response
            response = result.get('response', 'No response available')
            console.print(Panel(
                response,
                title="Agent Response",
                border_style="cyan"
            ))
            
            # Show verbose details if requested
            if verbose and 'details' in result:
                details_table = Table(title="Execution Details")
                details_table.add_column("Property", style="cyan")
                details_table.add_column("Value", style="white")
                
                for key, value in result['details'].items():
                    details_table.add_row(str(key), str(value))
                
                console.print(details_table)
                
        finally:
            await client.close()
    
    asyncio.run(_ask())


@app.command()
def status():
    """Display current system status and loaded resources."""
    async def _status():
        client = BackendClient()
        try:
            # Get health status
            health_status = await client.check_health()
            
            # Create status table
            status_table = Table(title="System Status")
            status_table.add_column("Component", style="cyan", no_wrap=True)
            status_table.add_column("Status", style="white")
            
            status_table.add_row("Backend Service", "🟢 Running" if health_status.get('status') == 'healthy' else "🔴 Unhealthy")
            status_table.add_row("Models Loaded", str(health_status.get('models_loaded', 'Unknown')))
            status_table.add_row("Memory Usage", f"{health_status.get('memory_usage', 'Unknown')} GB")
            status_table.add_row("Codebase Loaded", "✅ Yes" if health_status.get('codebase_loaded') else "❌ No")
            
            console.print(status_table)
            
        finally:
            await client.close()
    
    asyncio.run(_status())


@app.command()
def start_backend(
    port: int = typer.Option(8000, "--port", "-p", help="Port for backend service"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host for backend service"),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in background")
):
    """Start the backend GGUF memory service via backend manager."""
    backend_manager = get_backend_manager()
    backend_manager.default_port = port
    backend_manager.host = host
    success, pid = backend_manager.start_backend(detached=detach)
    if success:
        console.print(f"✅ [green]Backend started successfully[/green] (PID: {pid})")
    else:
        console.print("❌ [red]Failed to start backend service[/red]")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, 
        "--version", 
        "-V", 
        help="Show version and exit"
    ),
    skip_checks: bool = typer.Option(
        False,
        "--skip-checks",
        help="Skip pre-flight dependency validation (not recommended)"
    ),
    verbose_checks: bool = typer.Option(
        False,
        "--verbose-checks",
        help="Show detailed progress during dependency validation"
    ),
    user_input: Optional[str] = typer.Argument(
        None,
        help="Direct command input - natural language or special commands (/clear, /compact)"
    )
):
    """
    String CLI - Local AI coding assistant.
    
    A fully local AI coding assistant that rivals commercial tools with capabilities 
    including code generation, refactoring, quality review, live web research, 
    and automated file/terminal actions—all without cloud dependencies.
    
    Usage:
        string-cli "Analyze the main.py file and suggest improvements"
        string-cli /clear
        string-cli /compact
    """
    # Initialize STRING_HOME runtime directory
    try:
        string_home = ensure_string_home()
        initialize_default_configs()
        if verbose_checks:
            console.print(f"🏠 [blue]Runtime home:[/blue] {string_home}")
    except Exception as e:
        if not skip_checks:
            console.print(f"❌ [red]Failed to initialize runtime home:[/red] {e}")
            raise typer.Exit(code=1)
    
    # Handle version request before any other processing
    if version:
        string_home = get_string_home()
        console.print("string-cli v1.0.0 - Local AI Coding Assistant")
        console.print("Backend: FastAPI + Multi-Agent Architecture")
        console.print("Models: SmolLM3-3B, Gemma-3n-E4B-it, Qwen3-1.7B")
        console.print(f"Runtime home: {string_home}")
        raise typer.Exit()
    
    # Run runtime dependency checks before any command execution
    if not skip_checks:
        try:
            run_runtime_checks(verbose=verbose_checks or True)  # Always show details for debugging
        except DependencyError as e:
            console.print(f"\n❌ [red]Runtime checks failed:[/red]")
            console.print(f"{e.message}")
            if e.suggestions:
                console.print("\n💡 [cyan]Suggested fixes:[/cyan]")
                for suggestion in e.suggestions:
                    console.print(f"   • {suggestion}")
            console.print("\n💡 [yellow]Use --skip-checks to bypass validation (not recommended)[/yellow]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"\n⚠️  [yellow]Warning:[/yellow] Runtime check encountered an error: {e}")
            console.print("Proceeding anyway... some features may not work correctly.")
    
    # Ensure backend is running before any operations (except version/help/backend commands)
    backend_commands = ['start-backend', 'stop-backend', 'status', 'validate']
    skip_backend_start = (ctx.invoked_subcommand in backend_commands or 
                         any(cmd in str(ctx.command.name) for cmd in backend_commands))
    
    if not skip_checks and user_input is not None and not skip_backend_start:
        backend_manager = get_backend_manager()
        try:
            if not asyncio.run(backend_manager.ensure_backend_running()):
                console.print("❌ [red]Failed to start backend service[/red]")
                console.print("💡 [yellow]Try running with --skip-checks or check the logs[/yellow]")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"⚠️  [yellow]Backend auto-start error:[/yellow] {e}")
            console.print("Proceeding anyway... backend operations may fail.")
    
    # Auto-load current directory context if backend is available
    if not user_input and ctx.invoked_subcommand is None:
        async def _auto_load():
            client = BackendClient()
            try:
                # Check if backend is healthy
                health = await client.check_health()
                if health.get('status') == 'healthy':
                    current_dir = Path.cwd()
                    console.print(f"📁 [blue]Auto-loading codebase context from:[/blue] {current_dir}")
                    result = await client.load_codebase(str(current_dir))
                    console.print("✅ [green]Context loaded automatically[/green]")
            except Exception:
                # Silently fail auto-loading - user can manually load if needed
                pass
            finally:
                await client.close()
        
        try:
            asyncio.run(_auto_load())
        except Exception:
            pass
    
    # If user provided direct input, execute it
    if user_input:
        execute(user_input)
        return
    
    # Enter interactive session if no subcommand is provided
    if ctx.invoked_subcommand is None:
        if not skip_checks and not verbose_checks:
            console.print("✅ [green]All dependencies validated successfully![/green]\n")
        
        # Run interactive session
        try:
            asyncio.run(_run_interactive_session())
        except KeyboardInterrupt:
            console.print("\n👋 [blue]Goodbye![/blue]")
        except Exception as e:
            console.print(f"❌ [red]Interactive session failed:[/red] {e}")
            raise typer.Exit(1)


if __name__ == "__main__":
    app()