"""Self-Debug Orchestrator for JARVIS.

Coordinates empirical evidence collection, diagnostic fingerprinting,
Nemotron analysis, checkpoint verification, and issue tracking.
"""
from datetime import datetime
import json
import os
from typing import Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.core.logger import get_logger
from backend.diagnostics.nemotron_debugger import nemotron_debugger, NemotronDiagnosticReport
from backend.diagnostics.issue_tracker import issue_tracker, DiagnosticIssue
from backend.observability.command_tracer import command_tracer

logger = get_logger("SelfDebugManager")
console = Console()


class SelfDebugManager:
    """Singleton orchestrator for automated and on-demand self-debugging."""

    async def diagnose_latest_failure(self) -> Optional[NemotronDiagnosticReport]:
        """Trigger comprehensive root-cause analysis on the most recent failed command."""
        recent_traces = command_tracer.get_recent_traces(limit=5)
        failed_trace = next((t for t in recent_traces if t.verification_status == "FAIL" or t.error), None)

        if not failed_trace:
            console.print("[bold green]✅ No recent failures found in command trace history.[/bold green]")
            return None

        console.print(Panel(f"[bold cyan]🔍 RUNNING DIAGNOSTIC PIPELINE FOR {failed_trace.command_id}[/bold cyan]"))

        # Formulate empirical evidence
        report = await nemotron_debugger.diagnose_failure(
            command_text=failed_trace.raw_transcript,
            expected_intent=f"{failed_trace.domain}.{failed_trace.intent}",
            actual_result=failed_trace.error or failed_trace.verification_status,
            error_type="VERIFICATION_FAILED" if failed_trace.verification_status == "FAIL" else "RUNTIME_ERROR",
            error_stack=failed_trace.error,
            url_before=failed_trace.active_url,
            url_after=failed_trace.active_url,
            playwright_trace_path=failed_trace.playwright_trace_path,
            domain=failed_trace.domain,
        )

        # Register Issue
        issue = issue_tracker.create_issue(
            domain=failed_trace.domain,
            title=f"Failure in {failed_trace.domain}: '{failed_trace.raw_transcript}'",
            command=failed_trace.raw_transcript,
            expected=f"{failed_trace.domain}.{failed_trace.intent}",
            actual=failed_trace.error or failed_trace.verification_status,
            severity="ERROR",
            root_cause=report.rootCause,
            affected_layer=report.affectedLayer,
            confidence=report.confidence,
            proposed_fix=report.recommendedFix,
        )

        # Render Issue Card
        self.render_issue_card(issue, report)
        return report

    def render_issue_card(self, issue: DiagnosticIssue, report: NemotronDiagnosticReport) -> None:
        """Render a structured developer diagnostic issue card in the CLI."""
        card_text = (
            f"[bold magenta]ISSUE #{issue.issue_id}[/bold magenta]\n"
            f"[bold]Command:[/bold]      \"{issue.command}\"\n"
            f"[bold]Expected:[/bold]     {issue.expected}\n"
            f"[bold]Actual:[/bold]       {issue.actual}\n"
            f"[bold]Failure Type:[/bold] {report.issueType}\n"
            f"[bold]Layer:[/bold]        {report.affectedLayer}\n"
            f"[bold]Debugger:[/bold]     NVIDIA Nemotron (nvidia/nemotron-3.5-lightning:free)\n\n"
            f"[bold yellow]ROOT CAUSE:[/bold yellow]\n{report.rootCause}\n\n"
            f"[bold green]PROPOSED FIX:[/bold green]\n{report.recommendedFix}\n\n"
            f"[bold cyan]REPRODUCTION TEST:[/bold cyan]\n{report.reproductionTest}\n\n"
            f"[bold]Confidence:[/bold]   {int(report.confidence * 100)}%\n"
            f"[bold]Status:[/bold]       {issue.status}"
        )
        console.print(Panel(card_text, title=f"🚨 DIAGNOSTIC REPORT [{issue.issue_id}]", border_style="bright_yellow"))


# Global Singleton Self Debug Manager
self_debug_manager = SelfDebugManager()
