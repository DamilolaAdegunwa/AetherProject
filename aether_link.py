import os
import sys
import time
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live

from aether_core import PERSONAS, process_file_context, AetherEngine, DEFAULT_MODEL

class AetherLinkCLI:
    def __init__(self):
        self.console = Console()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.console.print(Panel(
                "[bold red]GEMINI_API_KEY is not set.[/bold red]\n\n"
                "Please configure your API key using one of the following methods:\n"
                "  1. Create a [bold cyan].env[/bold cyan] file in this directory:\n"
                "     [green]GEMINI_API_KEY=your_api_key_here[/green]\n\n"
                "  2. Or export it in your terminal session:\n"
                "     [green]export GEMINI_API_KEY=\"your_api_key_here\"[/green]\n\n"
                "Get an API key from Google AI Studio:\n"
                "  https://aistudio.google.com/app/apikey",
                title="Authentication Required",
                border_style="red"
            ))
            sys.exit(1)

        try:
            self.engine = AetherEngine(api_key=api_key, model=DEFAULT_MODEL)
        except Exception as e:
            self.console.print(f"[bold red]Initialization Failed:[/bold red] {e}")
            sys.exit(1)

    def switch_persona(self, key: str):
        if self.engine.set_persona(key):
            persona = PERSONAS[key]
            self.console.print(Panel(
                f"[bold green]Persona Switched:[/bold green] [bold magenta]{persona['name']}[/bold magenta] {persona['icon']}\n"
                f"[dim italic]\"{self.engine.system_instruction}\"[/dim italic]",
                title="Persona Updated",
                border_style="magenta"
            ))
        else:
            self.console.print(f"[bold red]Unknown persona key:[/bold red] {key}")

    def show_personas_table(self):
        table = Table(title="Available Personas & Commands", border_style="cyan", show_header=True)
        table.add_column("Command", style="bold yellow", width=18)
        table.add_column("Persona / Action", style="bold cyan", width=24)
        table.add_column("Description / Instruction", style="dim", width=44)
        table.add_column("Active", justify="center", width=8)

        for key, p in PERSONAS.items():
            cmd_str = ", ".join(p["commands"])
            is_active = "✅" if key == self.engine.active_persona else ""
            table.add_row(cmd_str, f"{p['icon']} {p['name']}", p["system_instruction"], is_active)

        table.add_section()
        table.add_row("/file <path> [prompt]", "File Context", "Inject local file content into the prompt", "")
        table.add_row("@<filepath>", "Inline File Tag", "Mention @filename anywhere in your question", "")
        table.add_row("/save [filename]", "Save Session", "Export chat history to a Markdown file", "")
        table.add_row("/clear", "Clear Memory", "Reset conversation history to start fresh", "")
        table.add_row("/exit, /quit", "Shutdown", "Exit Aether-Link Terminal", "")

        self.console.print(table)

    def run(self):
        active_p = PERSONAS[self.engine.active_persona]
        self.console.print(Panel.fit(
            f"[bold green]Aether-Link Terminal v1.0[/bold green]\n"
            f"Status: [cyan]Online[/cyan] | Model: [cyan]{self.engine.model}[/cyan] | Active Persona: [magenta]{active_p['name']}[/magenta] {active_p['icon']}\n"
            f"[dim]Features: [bold yellow]Streaming[/bold yellow] | [bold yellow]/file <path>[/bold yellow] | [bold yellow]@file[/bold yellow] | [bold yellow]/save[/bold yellow] | [bold yellow]/coder[/bold yellow] | [bold yellow]/writer[/bold yellow] | [bold yellow]/help[/bold yellow][/dim]",
            border_style="blue"
        ))
        
        while True:
            try:
                active_p = PERSONAS[self.engine.active_persona]
                prompt_label = f"\n[bold cyan]Query ({active_p['name']})[/bold cyan]"
                user_input = Prompt.ask(prompt_label)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            cleaned_input = user_input.strip()
            if not cleaned_input:
                continue

            if cleaned_input.lower() in ["exit", "quit", "bye", "/exit", "/quit", "/bye"]:
                self.console.print("[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            cmd_lower = cleaned_input.lower()
            if cmd_lower == "/coder":
                self.switch_persona("coder")
                continue
            elif cmd_lower == "/writer":
                self.switch_persona("writer")
                continue
            elif cmd_lower in ["/researcher", "/default"]:
                self.switch_persona("researcher")
                continue
            elif cmd_lower in ["/personas", "/help"]:
                self.show_personas_table()
                continue
            elif cmd_lower == "/clear":
                self.engine.clear_history()
                self.console.print("[bold yellow]Conversation history and session log cleared.[/bold yellow]")
                continue
            elif cmd_lower.startswith("/save"):
                parts = cleaned_input.split(maxsplit=1)
                custom_name = parts[1].strip() if len(parts) > 1 else None
                saved_path = self.engine.export_session_to_markdown(Path(custom_name) if custom_name else None)
                self.console.print(f"[bold green]Session exported successfully to:[/bold green] [cyan]{saved_path}[/cyan]")
                continue

            # Process file context
            prompt_to_send, loaded_files, err = process_file_context(cleaned_input)
            if err:
                self.console.print(f"[bold red]{err}[/bold red]")
                continue

            if loaded_files:
                files_badge = ", ".join([f"[cyan]{f}[/cyan] ({lines} lines)" for f, lines in loaded_files])
                self.console.print(f"[dim blue]📂 Injected file context:[/dim blue] {files_badge}")

            active_p = PERSONAS[self.engine.active_persona]
            self.console.print(f"\n[bold magenta]{active_p['icon']} Aether-Link ({active_p['name']}):[/bold magenta]")
            
            start_time = time.time()
            full_response_text = ""
            usage_info = None

            try:
                with Live(Markdown(""), console=self.console, refresh_per_second=15) as live:
                    for chunk in self.engine.stream_query(prompt_to_send):
                        if chunk.text:
                            full_response_text += chunk.text
                            live.update(Markdown(full_response_text))
                        if getattr(chunk, "usage_metadata", None):
                            usage_info = chunk.usage_metadata

                elapsed = time.time() - start_time
                metrics = f"⏱️ {elapsed:.2f}s | 🤖 {self.engine.model}"
                if usage_info and getattr(usage_info, "total_token_count", None):
                    metrics += f" | 🔢 Tokens: {usage_info.total_token_count} (Prompt: {usage_info.prompt_token_count}, Output: {usage_info.candidates_token_count})"

                self.console.print(f"[dim]{metrics}[/dim]")
                self.console.print("-" * 40)

                self.engine.record_exchange(cleaned_input, full_response_text, metrics)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Response generation interrupted by user.[/yellow]")
                self.console.print("-" * 40)
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app = AetherLinkCLI()
    app.run()
