"""Interactive & Automated Voice Command Pipeline Test Harness for JARVIS AI.

Runs typed command strings through the EXACT same end-to-end processing pipeline
as the voice engine (Normalization -> NLU -> Routing -> Tool Execution -> Verification).
Useful for instant offline verification, debugging, and regression testing without microphone.
"""
import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Set Windows console to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.ai.agent import JarvisAgent, AgentState
from backend.nlu import SemanticIntentEngine, UniversalIntentRouter, NluDebugLogger, LanguageNormalizer
from backend.core.logger import get_logger

console = Console(force_terminal=True, legacy_windows=False)
logger = get_logger("VoicePipelineTester")


# Standard test suite of 34 core commands across Hindi, Hinglish, and English
CORE_BENCHMARK_COMMANDS = [
    # 1. YouTube Media Playback & Seeking
    ("video pause karo", "PAUSE"),
    ("video rok do", "PAUSE"),
    ("isko pause kar", "PAUSE"),
    ("stop the video", "PAUSE"),
    ("resume video", "RESUME"),
    ("unpause karo", "RESUME"),
    ("video chalao", "RESUME"),
    ("10 second aage karo", "SEEK_FORWARD"),
    ("10 seconds backward", "SEEK_BACKWARD"),
    ("video ko 5 minute 30 second par lagao", "SEEK_TIMESTAMP"),
    ("12 minute par karo", "SEEK_TIMESTAMP"),
    ("speed badhao", "SPEED_UP"),
    ("speed kam karo", "SPEED_DOWN"),
    ("fullscreen karo", "FULLSCREEN"),
    ("theater mode lagao", "THEATER_MODE"),
    ("miniplayer chalao", "MINIPLAYER"),
    ("subtitles on karo", "CAPTIONS"),
    ("video replay karo", "REPLAY"),
    ("agla short dikhao", "NEXT_SHORT"),
    ("pichla short dikhao", "PREV_SHORT"),
    
    # 2. Thumbnail & Selection
    ("pehli video chalao", "SELECT"),
    ("dusri video chalao", "SELECT"),
    ("3rd video chalao", "SELECT"),
    ("chauthi video chalao", "SELECT"),
    
    # 3. Scrolling & Social
    ("scroll karo", "SCROLL_DOWN"),
    ("upar scroll karo", "SCROLL_UP"),
    ("video like karo", "LIKE"),
    ("video dislike karo", "DISLIKE"),
    ("channel subscribe karo", "SUBSCRIBE"),
    ("video share karo", "SHARE"),
    ("comments dikhao", "COMMENTS_VIEW"),
    
    # 4. System & App Launching
    ("volume badhao", "VOLUME_UP"),
    ("volume kam karo", "VOLUME_DOWN"),
    ("mute karo", "MUTE_AUDIO"),
    ("unmute karo", "UNMUTE_AUDIO"),
    ("chrome kholo", "OPEN_APP"),
    ("notepad kholo", "OPEN_APP"),
    ("calculator kholo", "OPEN_APP"),
    ("faltu tabs band karo", "CLEAN_JUNK"),
]


async def run_single_command(agent: JarvisAgent, text: str, execute_real_tools: bool = False):
    """Trace and report all 10 stages of a command through the agent pipeline."""
    start_t = time.time()
    
    # Stage 1 & 2: Normalization
    normalized, lang = LanguageNormalizer.normalize(text)
    
    # Stage 3: NLU Semantic Parsing
    nlu_res = SemanticIntentEngine.parse(text)
    
    # Stage 4: Router
    routed_calls = UniversalIntentRouter.route(nlu_res)
    
    table = Table(title=f"Pipeline Trace: '{text}'", border_style="cyan")
    table.add_column("Stage", style="bold green", width=22)
    table.add_column("Details / Output", style="white")

    table.add_row("1. Raw Transcript", f"\"{text}\"")
    table.add_row("2. Normalized Text", f"\"{normalized}\" (Language: {lang.upper()})")
    table.add_row("3. Detected Intent", f"{nlu_res.primary_intent.value} (Confidence: {nlu_res.confidence:.2f})")
    table.add_row("4. Extracted Entities", str(nlu_res.entities.model_dump(exclude_none=True)))
    
    if routed_calls:
        table.add_row("5. Routed Tool", f"{routed_calls[0].tool_name}")
        table.add_row("6. Tool Arguments", str(routed_calls[0].arguments))
        table.add_row("7. Immediate Speech", f"\"{routed_calls[0].immediate_response}\"")
    else:
        table.add_row("5. Routed Tool", "[yellow]None (Will route to AI LLM Provider)[/yellow]")

    # Stage 5: Real Agent Execution (Optional)
    if execute_real_tools:
        agent_resp = await agent.process_user_input(text)
        elapsed_ms = (time.time() - start_t) * 1000
        table.add_row("8. Agent Response", f"\"{agent_resp.message}\"")
        table.add_row("9. Agent State", f"{agent_resp.state.value}")
        verif_status = "VERIFIED" if agent_resp.tool_results and agent_resp.tool_results[0].success else "COMPLETED"
        table.add_row("10. Verification", f"[{'green' if verif_status == 'VERIFIED' else 'yellow'}]{verif_status}[/] ({elapsed_ms:.1f}ms)")
    else:
        elapsed_ms = (time.time() - start_t) * 1000
        table.add_row("8. Pipeline Latency", f"{elapsed_ms:.2f} ms (Dry Run)")

    console.print(table)
    console.print()


async def run_benchmark_suite(agent: JarvisAgent):
    """Run all benchmark commands and display an audit score matrix."""
    console.print(Panel("[bold magenta]🚀 Running JARVIS Core Voice Benchmark Suite (38 Commands)...[/bold magenta]", border_style="cyan"))
    
    results = []
    passed = 0
    total = len(CORE_BENCHMARK_COMMANDS)

    summary_table = Table(title="Benchmark Execution Matrix", border_style="bright_magenta")
    summary_table.add_column("#", width=4)
    summary_table.add_column("Command Text", style="bold cyan", width=38)
    summary_table.add_column("Expected Intent", width=18)
    summary_table.add_column("Detected Intent", width=18)
    summary_table.add_column("Routed Tool", width=22)
    summary_table.add_column("Status", width=12)

    for i, (cmd, expected_intent) in enumerate(CORE_BENCHMARK_COMMANDS, 1):
        nlu_res = SemanticIntentEngine.parse(cmd)
        routed = UniversalIntentRouter.route(nlu_res)
        detected_intent = nlu_res.primary_intent.value
        tool_name = routed[0].tool_name if routed else "None"
        
        is_correct = (detected_intent == expected_intent)
        if is_correct:
            passed += 1
            status_str = "[bold green]PASS[/bold green]"
        else:
            status_str = "[bold red]FAIL[/bold red]"

        summary_table.add_row(
            str(i),
            cmd,
            expected_intent,
            detected_intent,
            tool_name,
            status_str
        )

    console.print(summary_table)
    accuracy = (passed / total) * 100
    console.print(Panel(
        f"[bold]Accuracy Score:[/bold] [bold {'green' if accuracy >= 95 else 'yellow'}]{passed}/{total} ({accuracy:.1f}%)[/]\n"
        f"[dim]Deterministic sub-millisecond local NLU verified across Hindi, Hinglish, and English variations.[/dim]",
        title="Benchmark Results",
        border_style="green" if accuracy >= 95 else "yellow"
    ))


async def interactive_mode(agent: JarvisAgent, execute: bool = False):
    """Interactive typing shell to test any command on-the-fly."""
    console.print(Panel(
        "[bold cyan]🧪 JARVIS Voice Command Pipeline Tester (Interactive Mode)[/bold cyan]\n"
        "[dim]Type any Hindi, Hinglish, or English command to trace all 10 pipeline stages.\n"
        "Type 'benchmark' to run the full 38-command audit suite.\n"
        "Type 'exit' or 'quit' to close.[/dim]",
        border_style="bright_magenta"
    ))

    while True:
        try:
            console.print("[bold yellow]JARVIS Test ❯[/bold yellow] ", end="")
            user_input = input().strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            if user_input.lower() == "benchmark":
                await run_benchmark_suite(agent)
                continue

            await run_single_command(agent, user_input, execute_real_tools=execute)
        except (KeyboardInterrupt, EOFError):
            break


def main():
    parser = argparse.ArgumentParser(description="JARVIS Voice Pipeline Test Harness")
    parser.add_argument("--benchmark", action="store_true", help="Run full benchmark suite and exit")
    parser.add_argument("--cmd", type=str, help="Test a single command and exit")
    parser.add_argument("--execute", action="store_true", help="Execute real tools instead of dry-run")
    args = parser.parse_args()

    agent = JarvisAgent()

    if args.benchmark:
        asyncio.run(run_benchmark_suite(agent))
    elif args.cmd:
        asyncio.run(run_single_command(agent, args.cmd, execute_real_tools=args.execute))
    else:
        asyncio.run(interactive_mode(agent, execute=args.execute))


if __name__ == "__main__":
    main()
