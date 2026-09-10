import os
import sys
from pathlib import Path
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

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
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

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
            self.system_instruction = "You are Aether-Link, a high-level research assistant. Provide expert technical advice."
            # Use Chat session for multi-turn conversation memory and proper AFC handling
            self.chat = self.client.chats.create(
                model=MODEL_ID,
                config={'system_instruction': self.system_instruction}
            )
        except Exception as e:
            self.console.print(f"[bold red]Initialization Failed:[/bold red] {e}")
            sys.exit(1)

    def run(self):
        self.console.print(Panel.fit(
            f"[bold green]Aether-Link Terminal v1.0[/bold green]\n"
            f"Status: [cyan]Online[/cyan] | Model: [cyan]{MODEL_ID}[/cyan] | Memory: [cyan]Active[/cyan]",
            border_style="blue"
        ))
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]Query[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            if not user_input.strip():
                continue

            if user_input.lower().strip() in ["exit", "quit", "bye"]:
                self.console.print("[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            with self.console.status("[bold yellow]Gemini is thinking...[/bold yellow]"):
                try:
                    # Send message via chat session
                    response = self.chat.send_message(user_input)

                    # Display formatted response
                    self.console.print("\n[bold magenta]Aether-Link System Response:[/bold magenta]")
                    self.console.print(Markdown(response.text or ""))
                    self.console.print("-" * 40)
                    
                except Exception as e:
                    self.console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app = AetherLink()
    app.run()
