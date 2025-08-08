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
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

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

# Backend configuration
BACKEND_BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINTS = {
    "health": f"{BACKEND_BASE_URL}/health",
    "chat": f"{BACKEND_BASE_URL}/chat", 
    "load_codebase": f"{BACKEND_BASE_URL}/load_codebase",
    "execute_task": f"{BACKEND_BASE_URL}/execute_agentic_task",
    "clear": f"{BACKEND_BASE_URL}/clear",
    "compact": f"{BACKEND_BASE_URL}/compact"
}


class BackendClient:
    """HTTP client for communicating with the GGUF memory service backend."""
    
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> Dict[str, Any]:
        """Check if the backend service is running and healthy."""
        try:
            response = await self.client.get(API_ENDPOINTS["health"])
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Backend service unavailable: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Backend health check failed: {e}")
    
    async def load_codebase(self, path: str) -> Dict[str, Any]:
        """Load codebase into the backend memory system."""
        try:
            response = await self.client.post(
                API_ENDPOINTS["load_codebase"],
                json={"path": path}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise typer.Exit(f"Failed to load codebase: {e}")
        except httpx.HTTPStatusError as e:
            raise typer.Exit(f"Codebase loading failed: {e}")
    
    async def execute_task(self, prompt: str) -> Dict[str, Any]:
        """Execute an agentic task through the multi-agent orchestrator."""
        try:
            payload = {"prompt": prompt}
            
            response = await self.client.post(
                API_ENDPOINTS["execute_task"],
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
                API_ENDPOINTS["clear"],
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
                API_ENDPOINTS["compact"],
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
def status():
    """Show backend service and CLI status."""
    backend_manager = get_backend_manager()
    status_info = backend_manager.get_backend_status()
    
    console.print("🔍 [blue]String CLI Status[/blue]")
    console.print(f"Runtime home: {get_string_home()}")
    
    # Backend status
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
    
    # Check if already running
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
    """Start the backend GGUF memory service."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Find the project root to run the service from
    current_dir = Path.cwd()
    service_script = None
    
    # Look for run_gguf_service.py in current directory and parent directories
    search_paths = [current_dir] + list(current_dir.parents)
    for path in search_paths:
        potential_service = path / "run_gguf_service.py"
        if potential_service.exists():
            service_script = potential_service
            break
    
    if not service_script:
        console.print("❌ [red]Backend service script not found[/red]")
        console.print("💡 Make sure you're running from the project directory containing run_gguf_service.py")
        raise typer.Exit(1)
    
    console.print(f"🚀 [blue]Starting backend service...[/blue]")
    console.print(f"📁 Service script: {service_script}")
    console.print(f"🌐 Server: {host}:{port}")
    
    # Get the pipx python environment
    pipx_python = Path.home() / ".local" / "pipx" / "venvs" / "string-ai-coding-assistant" / "bin" / "python"
    if not pipx_python.exists():
        console.print("❌ [red]pipx environment not found[/red]")
        console.print("💡 Run: python3 setup_cli.py")
        raise typer.Exit(1)
    
    # Set environment variables
    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = str(port)
    
    if detach:
        # Run in background
        console.print("🔄 [yellow]Starting in background...[/yellow]")
        process = subprocess.Popen([
            str(pipx_python), str(service_script)
        ], env=env, cwd=service_script.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"✅ [green]Backend service started with PID {process.pid}[/green]")
        console.print(f"🔗 [cyan]API available at: http://{host}:{port}[/cyan]")
    else:
        # Run in foreground
        console.print("🔄 [yellow]Starting in foreground (Ctrl+C to stop)...[/yellow]")
        try:
            subprocess.run([str(pipx_python), str(service_script)], env=env, cwd=service_script.parent)
        except KeyboardInterrupt:
            console.print("\n🛑 [yellow]Backend service stopped[/yellow]")


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
    
    # Show help if no subcommand is provided
    if ctx.invoked_subcommand is None:
        if not skip_checks and not verbose_checks:
            console.print("✅ [green]All dependencies validated successfully![/green]\n")
        console.print(ctx.get_help(), color_system="auto")


if __name__ == "__main__":
    app()