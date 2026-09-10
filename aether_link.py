import os
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live

def load_dotenv(env_path: Path = None):
    """Load .env file into os.environ if present, without external dependencies."""
    if env_path is None:
        env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val

load_dotenv()

# Model configuration
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Available Assistant Personas
PERSONAS = {
    "researcher": {
        "name": "Research Assistant",
        "description": "High-level research assistant providing expert technical advice.",
        "system_instruction": "You are Aether-Link, a high-level research assistant. Provide expert technical advice.",
        "icon": "🔬",
        "commands": ["/researcher", "/default"],
    },
    "coder": {
        "name": "Expert Python Programmer",
        "description": "Expert Python programmer focused on clean, robust, and idiomatic code.",
        "system_instruction": "You are an expert Python programmer.",
        "icon": "💻",
        "commands": ["/coder"],
    },
    "writer": {
        "name": "Creative Novelist",
        "description": "Imaginative novelist crafting vivid narratives, stories, and evocative prose.",
        "system_instruction": "You are a creative novelist.",
        "icon": "✍️",
        "commands": ["/writer"],
    },
}

class AetherLink:
    def __init__(self):
        self.console = Console()
        self.session_log = []
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
            # Setting up the client using GEMINI_API_KEY from environment
            self.client = genai.Client(api_key=api_key)
            self.active_persona = "researcher"
            self.system_instruction = PERSONAS[self.active_persona]["system_instruction"]
            
            # Use Chat session for multi-turn conversation memory and proper AFC handling
            self.chat = self.client.chats.create(
                model=MODEL_ID,
                config={'system_instruction': self.system_instruction}
            )
        except Exception as e:
            self.console.print(f"[bold red]Initialization Failed:[/bold red] {e}")
            sys.exit(1)

    def set_persona(self, persona_key: str):
        """Switch assistant persona and re-initialize chat session while preserving conversation history."""
        if persona_key not in PERSONAS:
            self.console.print(f"[bold red]Unknown persona key:[/bold red] {persona_key}")
            return

        self.active_persona = persona_key
        persona = PERSONAS[persona_key]
        self.system_instruction = persona["system_instruction"]

        # Preserve existing conversation history while applying the new persona's system instruction
        history = self.chat.get_history() if hasattr(self, "chat") else []
        self.chat = self.client.chats.create(
            model=MODEL_ID,
            config={'system_instruction': self.system_instruction},
            history=history
        )

        self.console.print(Panel(
            f"[bold green]Persona Switched:[/bold green] [bold magenta]{persona['name']}[/bold magenta] {persona['icon']}\n"
            f"[dim italic]\"{self.system_instruction}\"[/dim italic]",
            title="Persona Updated",
            border_style="magenta"
        ))

    def show_personas_table(self):
        """Render a formatted table displaying available personas and slash commands."""
        table = Table(title="Available Personas & Commands", border_style="cyan", show_header=True)
        table.add_column("Command", style="bold yellow", width=18)
        table.add_column("Persona / Action", style="bold cyan", width=24)
        table.add_column("Description / Instruction", style="dim", width=44)
        table.add_column("Active", justify="center", width=8)

        for key, p in PERSONAS.items():
            cmd_str = ", ".join(p["commands"])
            is_active = "✅" if key == self.active_persona else ""
            table.add_row(cmd_str, f"{p['icon']} {p['name']}", p["system_instruction"], is_active)

        table.add_section()
        table.add_row("/file <path> [prompt]", "File Context", "Inject local file content into the prompt", "")
        table.add_row("@<filepath>", "Inline File Tag", "Mention @filename anywhere in your question", "")
        table.add_row("/save [filename]", "Save Session", "Export chat history to a Markdown file", "")
        table.add_row("/clear", "Clear Memory", "Reset conversation history to start fresh", "")
        table.add_row("/exit, /quit", "Shutdown", "Exit Aether-Link Terminal", "")

        self.console.print(table)

    def process_file_context(self, text: str):
        """
        Inspect prompt for file injection via `/file <path> [query]` or `@filepath` mentions.
        Returns: (processed_prompt, loaded_files_summary, error_message)
        """
        loaded = []
        max_file_size = 300_000  # ~300KB limit to avoid excessive token overhead

        # 1. Direct `/file <path> [optional query]` command
        if text.startswith("/file"):
            parts = text[5:].strip().split(maxsplit=1)
            if not parts:
                return None, [], "Usage: /file <path> [optional query]"
            filepath = parts[0]
            query = parts[1] if len(parts) > 1 else "Please review, analyze, and explain the contents of this file."
            p = Path(filepath)
            if not p.is_file():
                return None, [], f"File not found: {filepath}"
            if p.stat().st_size > max_file_size:
                return None, [], f"File too large ({p.stat().st_size // 1024} KB). Maximum supported size is 300 KB."
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                lines = len(content.splitlines())
                ext = p.suffix.lstrip(".") or "text"
                loaded.append((filepath, lines))
                processed = (
                    f"Context from file `{filepath}` ({lines} lines):\n"
                    f"```{ext}\n{content}\n```\n\n"
                    f"Task: {query}"
                )
                return processed, loaded, None
            except Exception as e:
                return None, [], f"Failed to read {filepath}: {e}"

        # 2. Inline `@<filepath>` mentions anywhere in query
        at_mentions = set(re.findall(r"@([a-zA-Z0-9_\-\.\/]+)", text))
        if at_mentions:
            file_blocks = []
            clean_text = text
            for ref in sorted(at_mentions):
                p = Path(ref)
                if p.is_file():
                    if p.stat().st_size > max_file_size:
                        self.console.print(f"[yellow]Skipping @{ref}: file exceeds 300 KB limit.[/yellow]")
                        continue
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                        lines = len(content.splitlines())
                        ext = p.suffix.lstrip(".") or "text"
                        loaded.append((ref, lines))
                        file_blocks.append(f"Context from file `{ref}` ({lines} lines):\n```{ext}\n{content}\n```")
                        clean_text = clean_text.replace(f"@{ref}", f"`{ref}`")
                    except Exception as e:
                        self.console.print(f"[yellow]Could not read @{ref}: {e}[/yellow]")
            if file_blocks:
                processed = "\n\n".join(file_blocks) + f"\n\nTask: {clean_text}"
                return processed, loaded, None

        return text, [], None

    def save_session(self, filename: str = None):
        """Export current session transcript into a readable Markdown document."""
        if not self.session_log:
            self.console.print("[yellow]No conversation history to save yet.[/yellow]")
            return

        save_dir = Path("saved_sessions")
        save_dir.mkdir(exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = save_dir / f"session_{timestamp}.md"
        else:
            file_path = Path(filename) if Path(filename).suffix else save_dir / f"{filename}.md"

        content = [
            f"# Aether-Link Session Log",
            f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Model:** `{MODEL_ID}`",
            f"- **Total Exchanges:** {len(self.session_log)}",
            "\n---\n"
        ]

        for item in self.session_log:
            content.append(f"### 👤 User ({item['persona']}) - {item['time']}")
            content.append(f"{item['query']}\n")
            content.append(f"### 🤖 Aether-Link")
            content.append(f"{item['response']}\n")
            if item.get("metrics"):
                content.append(f"> *{item['metrics']}*\n")
            content.append("---\n")

        file_path.write_text("\n".join(content), encoding="utf-8")
        self.console.print(f"[bold green]Session exported successfully to:[/bold green] [cyan]{file_path}[/cyan]")

    def run(self):
        self.console.print(Panel.fit(
            f"[bold green]Aether-Link Terminal v1.0[/bold green]\n"
            f"Status: [cyan]Online[/cyan] | Model: [cyan]{MODEL_ID}[/cyan] | Active Persona: [magenta]{PERSONAS[self.active_persona]['name']}[/magenta] {PERSONAS[self.active_persona]['icon']}\n"
            f"[dim]Features: [bold yellow]Streaming[/bold yellow] | [bold yellow]/file <path>[/bold yellow] | [bold yellow]@file[/bold yellow] | [bold yellow]/save[/bold yellow] | [bold yellow]/coder[/bold yellow] | [bold yellow]/writer[/bold yellow] | [bold yellow]/help[/bold yellow][/dim]",
            border_style="blue"
        ))
        
        while True:
            try:
                prompt_label = f"\n[bold cyan]Query ({PERSONAS[self.active_persona]['name']})[/bold cyan]"
                user_input = Prompt.ask(prompt_label)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            cleaned_input = user_input.strip()
            if not cleaned_input:
                continue

            # Exit command handling
            if cleaned_input.lower() in ["exit", "quit", "bye", "/exit", "/quit", "/bye"]:
                self.console.print("[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            # Slash command routing
            cmd_lower = cleaned_input.lower()
            if cmd_lower == "/coder":
                self.set_persona("coder")
                continue
            elif cmd_lower == "/writer":
                self.set_persona("writer")
                continue
            elif cmd_lower in ["/researcher", "/default"]:
                self.set_persona("researcher")
                continue
            elif cmd_lower in ["/personas", "/help"]:
                self.show_personas_table()
                continue
            elif cmd_lower == "/clear":
                self.chat = self.client.chats.create(
                    model=MODEL_ID,
                    config={'system_instruction': self.system_instruction}
                )
                self.session_log.clear()
                self.console.print("[bold yellow]Conversation history and session log cleared.[/bold yellow]")
                continue
            elif cmd_lower.startswith("/save"):
                parts = cleaned_input.split(maxsplit=1)
                custom_name = parts[1].strip() if len(parts) > 1 else None
                self.save_session(custom_name)
                continue

            # File injection processing
            prompt_to_send, loaded_files, err = self.process_file_context(cleaned_input)
            if err:
                self.console.print(f"[bold red]{err}[/bold red]")
                continue

            if loaded_files:
                files_badge = ", ".join([f"[cyan]{f}[/cyan] ({lines} lines)" for f, lines in loaded_files])
                self.console.print(f"[dim blue]📂 Injected file context:[/dim blue] {files_badge}")

            # Streaming query execution
            self.console.print(f"\n[bold magenta]{PERSONAS[self.active_persona]['icon']} Aether-Link ({PERSONAS[self.active_persona]['name']}):[/bold magenta]")
            
            start_time = time.time()
            full_response_text = ""
            usage_info = None

            try:
                # Live streaming markdown response
                with Live(Markdown(""), console=self.console, refresh_per_second=15) as live:
                    for chunk in self.chat.send_message_stream(prompt_to_send):
                        if chunk.text:
                            full_response_text += chunk.text
                            live.update(Markdown(full_response_text))
                        if getattr(chunk, "usage_metadata", None):
                            usage_info = chunk.usage_metadata

                elapsed = time.time() - start_time
                metrics = f"⏱️ {elapsed:.2f}s | 🤖 {MODEL_ID}"
                if usage_info and getattr(usage_info, "total_token_count", None):
                    metrics += f" | 🔢 Tokens: {usage_info.total_token_count} (Prompt: {usage_info.prompt_token_count}, Output: {usage_info.candidates_token_count})"

                self.console.print(f"[dim]{metrics}[/dim]")
                self.console.print("-" * 40)

                # Record in session transcript
                self.session_log.append({
                    "query": cleaned_input,
                    "response": full_response_text,
                    "persona": PERSONAS[self.active_persona]["name"],
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "metrics": metrics
                })

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Response generation interrupted by user.[/yellow]")
                self.console.print("-" * 40)
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app = AetherLink()
    app.run()
