import os
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

# --- YOUR CONFIGURATION ---
API_KEY = "AQ.Ab8RN6Jl_ZLppeYX7rPM_n1GjFlBkF26PP82pt4GQ3SVN_fmQQ"
MODEL_ID = "gemini-3.6-flash" 

class AetherLink:
    def __init__(self):
        self.console = Console()
        try:
            # Setting up the client
            self.client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1alpha'})
            self.history = [] 
            self.system_instruction = "You are Aether-Link, a high-level research assistant. Provide expert technical advice."
        except Exception as e:
            self.console.print(f"[bold red]Initialization Failed:[/bold red] {e}")

    def run(self):
        self.console.print(Panel.fit("[bold green]Aether-Link Terminal v1.0[/bold green]\nStatus: Online | Memory: Active", border_style="blue"))
        
        while True:
            user_input = Prompt.ask("\n[bold cyan]Query[/bold cyan]")

            if user_input.lower() in ["exit", "quit", "bye"]:
                self.console.print("[yellow]Shutting down Aether-Link... Goodbye.[/yellow]")
                break

            with self.console.status("[bold yellow]Gemini is thinking...[/bold yellow]"):
                try:
                    # Generate the response
                    response = self.client.models.generate_content(
                        model=MODEL_ID,
                        contents=self.history + [user_input],
                        config={'system_instruction': self.system_instruction}
                    )
                    
                    # Update History for conversation memory
                    self.history.append(user_input)
                    self.history.append(response.text)

                    # Display formatted response
                    self.console.print("\n[bold magenta]Aether-Link System Response:[/bold magenta]")
                    self.console.print(Markdown(response.text))
                    self.console.print("-" * 40)
                    
                except Exception as e:
                    self.console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app = AetherLink()
    app.run()
