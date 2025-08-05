#!/usr/bin/env python3
"""
Sync Shared Script

This script automates copying backend files that the CLI needs access to
into the cli/shared/ directory. This maintains separation of concerns while
allowing the CLI to reuse backend components like API clients and data models.

Usage:
    python scripts/sync_shared.py [--dry-run]
"""

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

import typer


def main(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be copied without actually copying"
    )
):
    """Sync necessary backend files to cli/shared/ directory."""
    
    # Define source -> destination mappings
    sync_mappings: List[Tuple[str, str]] = [
        # Backend API models and response classes
        ("run_gguf_service.py", "api_models.py"),
        # Configuration files
        ("config/models.yaml", "models.yaml"),
        ("config/agent_intent_registry.yaml", "agent_intent_registry.yaml"),
        # Core backend utilities if needed by CLI
        # ("src/core/resource_manager.py", "resource_manager.py"),
    ]
    
    project_root = Path(__file__).parent.parent
    cli_shared_dir = project_root / "cli" / "shared"
    
    # Ensure cli/shared directory exists
    if not dry_run:
        cli_shared_dir.mkdir(parents=True, exist_ok=True)
    
    typer.echo(f"Project root: {project_root}")
    typer.echo(f"CLI shared directory: {cli_shared_dir}")
    typer.echo()
    
    if not sync_mappings:
        typer.echo("✅ No sync mappings configured yet.")
        typer.echo("Edit this script to add source -> destination mappings as needed.")
        return
    
    copied_count = 0
    
    for source_path, dest_path in sync_mappings:
        source = project_root / source_path
        destination = cli_shared_dir / dest_path
        
        if not source.exists():
            typer.echo(f"⚠️  Source file not found: {source}", err=True)
            continue
        
        if dry_run:
            typer.echo(f"[DRY RUN] Would copy: {source} -> {destination}")
        else:
            try:
                # Ensure destination directory exists
                destination.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source, destination)
                typer.echo(f"✅ Copied: {source_path} -> cli/shared/{dest_path}")
                copied_count += 1
                
            except Exception as e:
                typer.echo(f"❌ Failed to copy {source_path}: {e}", err=True)
    
    if not dry_run:
        typer.echo(f"\n✅ Sync complete! Copied {copied_count} files.")
    else:
        typer.echo(f"\n[DRY RUN] Would copy {len(sync_mappings)} files.")


if __name__ == "__main__":
    typer.run(main)