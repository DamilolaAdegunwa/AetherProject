import os
import sys
from pathlib import Path
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table

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
        table.add_column("Command", style="bold yellow", width=16)
        table.add_column("Persona", style="bold cyan", width=26)
        table.add_column("System Instruction", style="dim", width=46)
        table.add_column("Active", justify="center", width=8)

        for key, p in PERSONAS.items():
            cmd_str = ", ".join(p["commands"])
            is_active = "✅" if key == self.active_persona else ""
            table.add_row(cmd_str, f"{p['icon']} {p['name']}", p["system_instruction"], is_active)

        table.add_section()
        table.add_row("/clear", "Clear Memory", "Reset conversation history to start fresh", "")
        table.add_row("/exit, /quit", "Shutdown", "Exit Aether-Link Terminal", "")

        self.console.print(table)

    def run(self):
        self.console.print(Panel.fit(
            f"[bold green]Aether-Link Terminal v1.0[/bold green]\n"
            f"Status: [cyan]Online[/cyan] | Model: [cyan]{MODEL_ID}[/cyan] | Active Persona: [magenta]{PERSONAS[self.active_persona]['name']}[/magenta] {PERSONAS[self.active_persona]['icon']}\n"
            f"[dim]Type [bold yellow]/coder[/bold yellow], [bold yellow]/writer[/bold yellow], [bold yellow]/researcher[/bold yellow], or [bold yellow]/help[/bold yellow] to switch personas.[/dim]",
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

            # Check for exit commands
            if cleaned_input.lower() in ["exit", "quit", "bye", "/exit", "/quit", "/bye"]:
                self.console.print("[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            # Check for Persona Switcher commands
            cmd = cleaned_input.lower()
            if cmd == "/coder":
                self.set_persona("coder")
                continue
            elif cmd == "/writer":
                self.set_persona("writer")
                continue
            elif cmd in ["/researcher", "/default"]:
                self.set_persona("researcher")
                continue
            elif cmd in ["/personas", "/help"]:
                self.show_personas_table()
                continue
            elif cmd == "/clear":
                self.chat = self.client.chats.create(
                    model=MODEL_ID,
                    config={'system_instruction': self.system_instruction}
                )
                self.console.print("[bold yellow]Conversation history cleared. Fresh memory initialized.[/bold yellow]")
                continue

            # Standard prompt execution
            with self.console.status("[bold yellow]Gemini is thinking...[/bold yellow]"):
                try:
                    # Send message via chat session
                    response = self.chat.send_message(user_input)

                    # Display formatted response
                    self.console.print(f"\n[bold magenta]{PERSONAS[self.active_persona]['icon']} Aether-Link ({PERSONAS[self.active_persona]['name']}):[/bold magenta]")
                    self.console.print(Markdown(response.text or ""))
                    self.console.print("-" * 40)
                    
                except Exception as e:
                    self.console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app = AetherLink()
    app.run()
