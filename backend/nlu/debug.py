"""Developer Observability & Debug Panel for NLU pipeline."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from backend.nlu.models import NluDebugTrace

console = Console()


class NluDebugLogger:
    """Prints beautiful formatted developer debug trace on every interaction turn."""

    @classmethod
    def log_trace(cls, trace: NluDebugTrace) -> None:
        """Render a structured debug panel in the console."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="bold cyan", width=18)
        table.add_column("Value", style="white")

        table.add_row("Raw Transcript:", f"[italic yellow]\"{trace.raw_transcript}\"[/italic yellow]")
        table.add_row("Normalized:", f"[bold white]\"{trace.normalized_transcript}\"[/bold white]")
        table.add_row("Detected Language:", f"[green]{trace.detected_language.upper()}[/green]")
        table.add_row("Semantic Intent:", f"[bold magenta]{trace.intent}[/bold magenta] (Confidence: {trace.confidence:.2f})")
        table.add_row("Extracted Entities:", str(trace.entities))
        table.add_row("Target Application:", f"[bold blue]{trace.target_application or 'None'}[/bold blue]")
        table.add_row("Selected Tool:", f"[bold green]{trace.selected_tool or 'None'}[/bold green]")
        table.add_row("Tool Arguments:", str(trace.tool_arguments))

        if trace.execution_result:
            table.add_row("Execution Result:", f"[green]{trace.execution_result}[/green]")
        if trace.verification_status:
            table.add_row("Verification:", f"[bold green]{trace.verification_status}[/bold green]")
        if trace.error_or_clarification:
            table.add_row("Clarification / Info:", f"[bold yellow]{trace.error_or_clarification}[/bold yellow]")

        console.print(Panel(table, title="[bold cyan]🧠 JARVIS Universal NLU Engine Debug Trace[/bold cyan]", border_style="cyan"))
