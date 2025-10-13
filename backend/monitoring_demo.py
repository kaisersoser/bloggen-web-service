#!/usr/bin/env python3
"""
Monitoring Service Live Demonstration

This script demonstrates all monitoring features by making requests
to the monitoring endpoints and displaying formatted results.

Usage:
    python monitoring_demo.py

Prerequisites:
    - Backend running on http://localhost:8000
    - All services operational (DB, Redis)
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    import httpx
    import rich
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install httpx rich")
    sys.exit(1)

console = Console()
BASE_URL = "http://localhost:5000"


async def check_endpoint(client: httpx.AsyncClient, endpoint: str) -> dict:
    """Make request to endpoint and return JSON response."""
    try:
        response = await client.get(f"{BASE_URL}{endpoint}")
        return {
            "status_code": response.status_code,
            "data": response.json(),
            "response_time": response.headers.get("X-Response-Time", "N/A")
        }
    except Exception as e:
        return {
            "status_code": 0,
            "error": str(e),
            "data": None
        }


def display_health_check(name: str, result: dict) -> None:
    """Display formatted health check result."""
    if result["status_code"] != 200:
        console.print(f"[red]✗ {name}: Failed to connect[/red]")
        return
    
    data = result["data"]
    
    if "services" in data:
        # Comprehensive health check
        table = Table(title=f"🏥 {name}", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Response Time", justify="right")
        table.add_column("Details")
        
        for service_name, service_data in data["services"].items():
            status_icon = "✅" if service_data["healthy"] else "❌"
            status_text = "Healthy" if service_data["healthy"] else "Unhealthy"
            response_time = f"{service_data['response_time_ms']:.2f}ms"
            details = json.dumps(service_data["details"], indent=2) if service_data["details"] else "-"
            
            table.add_row(
                service_name.title(),
                f"{status_icon} {status_text}",
                response_time,
                details[:50] + "..." if len(details) > 50 else details
            )
        
        console.print(table)
    else:
        # Single service health check
        service_data = data
        status_icon = "✅" if service_data["healthy"] else "❌"
        status_text = "Healthy" if service_data["healthy"] else "Unhealthy"
        response_time = f"{service_data['response_time_ms']:.2f}ms"
        
        console.print(Panel(
            f"[bold]{status_icon} {status_text}[/bold]\n"
            f"Response Time: {response_time}\n"
            f"Details: {json.dumps(service_data['details'], indent=2)}",
            title=f"🏥 {name}",
            border_style="green" if service_data["healthy"] else "red"
        ))


def display_metrics(result: dict) -> None:
    """Display formatted metrics."""
    if result["status_code"] != 200:
        console.print("[red]✗ Metrics: Failed to connect[/red]")
        return
    
    data = result["data"]
    
    # Overall metrics
    metrics = data.get("metrics", {})
    table = Table(title="📊 Request Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Requests", str(metrics.get("total_requests", 0)))
    table.add_row("Successful Requests", f"[green]{metrics.get('successful_requests', 0)}[/green]")
    table.add_row("Failed Requests", f"[red]{metrics.get('failed_requests', 0)}[/red]")
    table.add_row("Avg Response Time", f"{metrics.get('avg_response_time', 0):.3f}s")
    table.add_row("Error Rate", f"{metrics.get('error_rate', 0):.2f}%")
    table.add_row("Requests/Minute", str(metrics.get('requests_per_minute', 0)))
    
    console.print(table)
    
    # System metrics
    system = data.get("system", {})
    if system:
        table = Table(title="💻 System Resources", show_header=True, header_style="bold magenta")
        table.add_column("Resource", style="cyan")
        table.add_column("Usage", justify="right")
        
        table.add_row("CPU", f"{system.get('cpu_percent', 0):.1f}%")
        table.add_row("Memory", f"{system.get('memory_percent', 0):.1f}%")
        table.add_row("Memory Used", f"{system.get('memory_used_mb', 0):.1f} MB")
        table.add_row("Memory Available", f"{system.get('memory_available_mb', 0):.1f} MB")
        table.add_row("Disk", f"{system.get('disk_usage_percent', 0):.1f}%")
        table.add_row("Open Connections", str(system.get('open_connections', 0)))
        table.add_row("Threads", str(system.get('thread_count', 0)))
        
        console.print(table)


def display_performance(result: dict) -> None:
    """Display formatted performance metrics."""
    if result["status_code"] != 200:
        console.print("[red]✗ Performance: Failed to connect[/red]")
        return
    
    data = result["data"]
    operations = data.get("operations", {})
    
    if not operations:
        console.print("[yellow]⚠️  No performance metrics recorded yet[/yellow]")
        return
    
    table = Table(title="⚡ Performance Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Operation", style="cyan")
    table.add_column("Executions", justify="right")
    table.add_column("Avg Duration", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    
    for op_name, op_data in operations.items():
        table.add_row(
            op_name,
            str(op_data.get("execution_count", 0)),
            f"{op_data.get('avg_duration', 0):.3f}s",
            f"{op_data.get('min_duration', 0):.3f}s",
            f"{op_data.get('max_duration', 0):.3f}s"
        )
    
    console.print(table)


async def main():
    """Run monitoring demonstration."""
    console.print("\n[bold cyan]🔍 Monitoring Service Live Demonstration[/bold cyan]\n")
    console.print(f"Base URL: {BASE_URL}")
    console.print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Health Checks
            task = progress.add_task("[cyan]Checking health endpoints...", total=5)
            
            console.rule("[bold]Health Checks[/bold]")
            
            health = await check_endpoint(client, "/health")
            display_health_check("Comprehensive Health Check", health)
            progress.update(task, advance=1)
            
            console.print()
            
            db_health = await check_endpoint(client, "/health/database")
            display_health_check("Database Health", db_health)
            progress.update(task, advance=1)
            
            console.print()
            
            redis_health = await check_endpoint(client, "/health/redis")
            display_health_check("Redis Health", redis_health)
            progress.update(task, advance=1)
            
            console.print()
            
            sse_health = await check_endpoint(client, "/health/sse")
            display_health_check("SSE Health", sse_health)
            progress.update(task, advance=1)
            
            console.print()
            
            system_health = await check_endpoint(client, "/health/system")
            display_health_check("System Health", system_health)
            progress.update(task, advance=1)
            
            console.print()
            console.rule("[bold]Metrics[/bold]")
            
            # Metrics
            task = progress.add_task("[cyan]Fetching metrics...", total=2)
            
            metrics = await check_endpoint(client, "/metrics")
            display_metrics(metrics)
            progress.update(task, advance=1)
            
            console.print()
            
            # Performance
            performance = await check_endpoint(client, "/metrics/performance")
            display_performance(performance)
            progress.update(task, advance=1)
    
    console.print("\n[bold green]✅ Monitoring demonstration complete![/bold green]\n")
    
    # Summary
    console.print(Panel(
        "[bold]Monitoring Endpoints Available:[/bold]\n\n"
        "Health Checks:\n"
        "  • GET /health - Comprehensive health check\n"
        "  • GET /health/database - Database health\n"
        "  • GET /health/redis - Redis health\n"
        "  • GET /health/sse - SSE health\n"
        "  • GET /health/system - System health\n\n"
        "Metrics:\n"
        "  • GET /metrics - Full system status\n"
        "  • GET /metrics/summary - Quick summary\n"
        "  • GET /metrics/performance - Performance metrics\n"
        "  • GET /metrics/system - System resources",
        title="📋 Monitoring API",
        border_style="blue"
    ))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)
