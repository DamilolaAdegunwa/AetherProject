import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from google import genai

def load_dotenv(env_path: Optional[Path] = None) -> None:
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

# Automatically load environment on import
load_dotenv()

# Model configuration
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# Personas definition
PERSONAS: Dict[str, Dict[str, Any]] = {
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

def process_file_context(text: str, max_file_size: int = 300_000) -> Tuple[Optional[str], List[Tuple[str, int]], Optional[str]]:
    """
    Parses a query for file context injection via:
      1. Direct `/file <path> [optional query]`
      2. Inline `@<filepath>` mentions
    Returns:
      (processed_prompt, list_of_(filepath, line_count), error_message)
    """
    loaded: List[Tuple[str, int]] = []

    # 1. Direct `/file` command
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
            return None, [], f"File too large ({p.stat().st_size // 1024} KB). Max supported size is {max_file_size // 1024} KB."
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

    # 2. Inline `@<filepath>` mentions
    at_mentions = set(re.findall(r"@([a-zA-Z0-9_\-\.\/]+)", text))
    if at_mentions:
        file_blocks = []
        clean_text = text
        for ref in sorted(at_mentions):
            p = Path(ref)
            if p.is_file():
                if p.stat().st_size > max_file_size:
                    continue
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    lines = len(content.splitlines())
                    ext = p.suffix.lstrip(".") or "text"
                    loaded.append((ref, lines))
                    file_blocks.append(f"Context from file `{ref}` ({lines} lines):\n```{ext}\n{content}\n```")
                    clean_text = clean_text.replace(f"@{ref}", f"`{ref}`")
                except Exception:
                    pass
        if file_blocks:
            processed = "\n\n".join(file_blocks) + f"\n\nTask: {clean_text}"
            return processed, loaded, None

    return text, [], None

class AetherEngine:
    """Core AI engine managing Gemini sessions, personas, streaming, and session logs."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please provide a valid Gemini API key.")

        self.model = model
        self.client = genai.Client(api_key=self.api_key)
        self.active_persona = "researcher"
        self.system_instruction = PERSONAS[self.active_persona]["system_instruction"]
        self.session_log: List[Dict[str, Any]] = []

        # Create active chat session
        self.chat = self.client.chats.create(
            model=self.model,
            config={'system_instruction': self.system_instruction}
        )

    def set_persona(self, persona_key: str) -> bool:
        """Switch persona and re-initialize chat session while retaining history."""
        if persona_key not in PERSONAS:
            return False

        self.active_persona = persona_key
        self.system_instruction = PERSONAS[persona_key]["system_instruction"]

        # Preserve existing conversation history
        history = self.chat.get_history() if hasattr(self, "chat") else []
        self.chat = self.client.chats.create(
            model=self.model,
            config={'system_instruction': self.system_instruction},
            history=history
        )
        return True

    def set_model(self, model_name: str) -> None:
        """Switch the underlying Gemini model and re-initialize chat session while preserving history."""
        self.model = model_name
        history = self.chat.get_history() if hasattr(self, "chat") else []
        self.chat = self.client.chats.create(
            model=self.model,
            config={'system_instruction': self.system_instruction},
            history=history
        )

    def clear_history(self) -> None:
        """Reset conversation memory and session logs."""
        self.chat = self.client.chats.create(
            model=self.model,
            config={'system_instruction': self.system_instruction}
        )
        self.session_log.clear()

    def stream_query(self, prompt: str):
        """
        Sends query to Gemini and returns an iterator of response chunks.
        """
        return self.chat.send_message_stream(prompt)

    def record_exchange(self, query: str, response: str, metrics: str = "") -> None:
        """Add an exchange to the persistent session log."""
        self.session_log.append({
            "query": query,
            "response": response,
            "persona": PERSONAS[self.active_persona]["name"],
            "icon": PERSONAS[self.active_persona]["icon"],
            "time": datetime.now().strftime("%H:%M:%S"),
            "metrics": metrics
        })

    def export_session_to_markdown(self, target_path: Optional[Path] = None) -> Path:
        """Export session log to a Markdown file."""
        save_dir = Path("saved_sessions")
        save_dir.mkdir(exist_ok=True)

        if not target_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = save_dir / f"session_{timestamp}.md"
        else:
            if not target_path.suffix:
                target_path = target_path.with_suffix(".md")

        content = [
            f"# Aether-Link Session Log",
            f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Model:** `{self.model}`",
            f"- **Exchanges:** {len(self.session_log)}",
            "\n---\n"
        ]

        for item in self.session_log:
            content.append(f"### {item['icon']} User ({item['persona']}) - {item['time']}")
            content.append(f"{item['query']}\n")
            content.append(f"### 🤖 Aether-Link")
            content.append(f"{item['response']}\n")
            if item.get("metrics"):
                content.append(f"> *{item['metrics']}*\n")
            content.append("---\n")

        target_path.write_text("\n".join(content), encoding="utf-8")
        return target_path
