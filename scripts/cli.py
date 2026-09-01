"""Interactive terminal client for JARVIS AI Assistant.

Allows direct interaction, testing of tool execution, and confirmation workflows
with rich visual formatting in Windows Terminal / PowerShell.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.ai.agent import AgentState, JarvisAgent
from backend.core.config import get_settings
from backend.database.repositories import task_history_repo
from backend.tools.registry import default_registry

console = Console()
settings = get_settings()


def print_banner():
    """Display the JARVIS startup banner."""
    banner_text = Text()
    banner_text.append("⚡ J.A.R.V.I.S. AI ASSISTANT ⚡\n", style="bold cyan")
    banner_text.append(f"Operating System: Windows | User: {settings.USER_NAME}\n", style="dim")
    banner_text.append(f"AI Provider: {settings.AI_PROVIDER.upper()} | Model: {settings.AI_MODEL if settings.AI_PROVIDER == 'mock' else settings.OPENROUTER_MODEL}\n", style="dim")
    banner_text.append("Commands: 'tools' | 'history' | 'stats' | 'reset' | 'clear' | 'exit'", style="italic yellow")

    console.print(Panel(banner_text, border_style="cyan", title="System Active"))


def print_tools_table():
    """Display registered tools in a formatted table with categories."""
    table = Table(title="🔧 Registered JARVIS Tools", border_style="bright_blue")
    table.add_column("Tool Name", style="bold green")
    table.add_column("Category", style="cyan")
    table.add_column("Permission Level", style="magenta")
    table.add_column("Description", style="white")

    for tool in default_registry.list_tools():
        table.add_row(
            tool.name,
            tool.category.value,
            f"Level {tool.permission_level.value}",
            tool.description,
        )
    console.print(table)


def print_history():
    """Display recent command execution history."""
    records = task_history_repo.get_recent(limit=15)
    if not records:
        console.print("[dim]No task history recorded yet.[/dim]\n")
        return

    table = Table(title="📜 Recent Task Execution History", border_style="yellow")
    table.add_column("ID", style="dim")
    table.add_column("Timestamp", style="dim")
    table.add_column("Command", style="cyan")
    table.add_column("Action", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Time (ms)", style="magenta")

    for r in records:
        status_style = "bold green" if r.status == "SUCCESS" else "bold red" if r.status == "FAILED" else "bold yellow"
        table.add_row(
            str(r.id),
            str(r.timestamp or ""),
            r.command,
            r.action or "-",
            f"[{status_style}]{r.status}[/{status_style}]",
            str(r.execution_time_ms),
        )
    console.print(table)


def print_stats():
    """Display command execution statistics."""
    stats = task_history_repo.get_stats()
    table = Table(title="📊 JARVIS Usage & Health Statistics", border_style="green")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Total Commands Processed", str(stats.get("total_commands", 0)))
    table.add_row("Successful Executions", str(stats.get("successful_commands", 0)))
    table.add_row("Success Rate", f"{stats.get('success_rate_percent', 100.0)}%")

    top_tools = stats.get("top_tools", [])
    top_str = ", ".join([f"{t['tool']} ({t['count']})" for t in top_tools]) if top_tools else "None"
    table.add_row("Most Used Tools", top_str)

    console.print(table)


async def main():
    """Main interactive terminal loop."""
    print_banner()
    agent = JarvisAgent()

    while True:
        try:
            # Format prompt based on agent state
            if agent.state == AgentState.AWAITING_CONFIRMATION:
                prompt_style = "bold red"
                prompt_prefix = "[CONFIRM (y/n)] ❯ "
            else:
                prompt_style = "bold cyan"
                prompt_prefix = f"[{settings.USER_NAME}] ❯ "

            console.print(prompt_prefix, style=prompt_style, end="")
            user_input = input().strip()

            if not user_input:
                continue

            # Handle built-in CLI commands
            cmd_lower = user_input.lower()
            if cmd_lower in ["exit", "quit", "q"]:
                console.print("\n[bold yellow]JARVIS powering down. Have a productive day, Sir.[/bold yellow]")
                break
            elif cmd_lower == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_banner()
                continue
            elif cmd_lower == "tools":
                print_tools_table()
                continue
            elif cmd_lower == "history":
                print_history()
                continue
            elif cmd_lower == "stats":
                print_stats()
                continue
            elif cmd_lower == "reset":
                agent.reset_conversation()
                console.print("[green]✓ Agent conversation history and state reset.[/green]\n")
                continue
            elif cmd_lower == "help":
                console.print(Panel(
                    "Try commands like:\n"
                    " • 'Hello Jarvis'\n"
                    " • 'What time is it?'\n"
                    " • 'Battery status'\n"
                    " • 'Storage status'\n"
                    " • 'Network status'\n"
                    " • 'System status'\n"
                    " • 'history' (view execution log)\n"
                    " • 'stats' (view health statistics)\n"
                    " • 'tools' (view registered functions)\n"
                    " • 'reset' (clear context memory)\n"
                    " • 'exit' (shut down)",
                    title="💡 Quick Help",
                    border_style="yellow",
                ))
                continue

            # Show thinking indicator
            with console.status("[bold green]JARVIS is processing...[/bold green]", spinner="dots"):
                response = await agent.process_user_input(user_input)

            # Display JARVIS output
            if response.state == AgentState.AWAITING_CONFIRMATION:
                console.print(Panel(
                    f"[bold yellow]⚠️ Permission Required:[/bold yellow]\n{response.message}",
                    border_style="red",
                    title="Security Confirmation",
                ))
            elif response.state == AgentState.ERROR:
                console.print(Panel(
                    f"[bold red]❌ Error:[/bold red] {response.message}",
                    border_style="red",
                ))
            else:
                console.print(f"[bold cyan]JARVIS:[/bold cyan] {response.message}\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Interrupted. JARVIS powering down.[/bold yellow]")
            break
        except Exception as exc:
            console.print(f"\n[bold red]Unhandled Exception:[/bold red] {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
