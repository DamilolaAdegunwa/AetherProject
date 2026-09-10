import os
import sys
import json
import time
import socket
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlparse

from aether_core import (
    PERSONAS,
    process_file_context,
    AetherEngine,
    DEFAULT_MODEL,
    load_dotenv
)

# Ensure environment is loaded
load_dotenv()

# Global engine instance for the web server
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("\n[ERROR] GEMINI_API_KEY is not set.")
    print("Please set it in your .env file or export it:")
    print("  export GEMINI_API_KEY=\"your_api_key_here\"\n")
    sys.exit(1)

try:
    engine = AetherEngine(api_key=api_key, model=DEFAULT_MODEL)
except Exception as e:
    print(f"\n[ERROR] Failed to initialize Gemini engine: {e}\n")
    sys.exit(1)

STATIC_DIR = Path(__file__).resolve().parent / "static"

class AetherWebHandler(BaseHTTPRequestHandler):
    server_version = "AetherWeb/1.0"

    def log_message(self, format, *args):
        try:
            sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}\n")
        except Exception:
            pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(STATIC_DIR / "index.html", "text/html")
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = STATIC_DIR / rel_path
            if ".." in rel_path or not file_path.is_file():
                self.send_error(404, "File Not Found")
                return

            ext = file_path.suffix.lower()
            mime_types = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon"
            }
            mime = mime_types.get(ext, "application/octet-stream")
            self._serve_file(file_path, mime)

        elif path == "/api/status":
            active_p = PERSONAS[engine.active_persona]
            self._send_json({
                "status": "online",
                "model": engine.model,
                "persona": engine.active_persona,
                "persona_name": active_p["name"],
                "icon": active_p["icon"],
                "system_instruction": engine.system_instruction,
                "exchanges_count": len(engine.session_log)
            })

        elif path == "/api/personas":
            self._send_json({
                "personas": PERSONAS,
                "active": engine.active_persona
            })

        elif path == "/api/export":
            content = [
                f"# Aether-Link Web Session Log",
                f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **Model:** `{engine.model}`",
                f"- **Exchanges:** {len(engine.session_log)}",
                "\n---\n"
            ]
            for item in engine.session_log:
                content.append(f"### {item['icon']} User ({item['persona']}) - {item['time']}")
                content.append(f"{item['query']}\n")
                content.append(f"### 🤖 Aether-Link")
                content.append(f"{item['response']}\n")
                if item.get("metrics"):
                    content.append(f"> *{item['metrics']}*\n")
                content.append("---\n")

            md_data = "\n".join(content).encode("utf-8")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=\"aether_session_{timestamp}.md\"")
            self.send_header("Content-Length", str(len(md_data)))
            self.end_headers()
            self.wfile.write(md_data)

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/persona":
            body = self._read_json_body()
            target_key = body.get("persona")
            if target_key in PERSONAS:
                engine.set_persona(target_key)
                p = PERSONAS[target_key]
                self._send_json({
                    "success": True,
                    "persona": target_key,
                    "name": p["name"],
                    "icon": p["icon"],
                    "system_instruction": p["system_instruction"]
                })
            else:
                self.send_error(400, f"Unknown persona: {target_key}")

        elif path == "/api/model":
            body = self._read_json_body()
            target_model = body.get("model")
            if target_model:
                engine.set_model(target_model)
                self._send_json({"success": True, "model": target_model})
            else:
                self.send_error(400, "Missing model field")

        elif path == "/api/clear":
            engine.clear_history()
            self._send_json({"success": True, "message": "History cleared"})

        elif path == "/api/chat":
            # Server-Sent Events (SSE) Streaming Endpoint
            body = self._read_json_body()
            raw_query = body.get("query", "").strip()
            files_payload = body.get("files", [])

            # Process inline @mentions / /file commands
            prompt_to_send, loaded_from_mentions, err = process_file_context(raw_query)
            if err:
                self._send_sse_error(err)
                return

            # Append files sent via frontend drag-and-drop / attachment
            if files_payload:
                file_blocks = []
                for f in files_payload:
                    fname = f.get("name", "file")
                    content = f.get("content", "")
                    lines = f.get("lines", len(content.splitlines()))
                    ext = Path(fname).suffix.lstrip(".") or "text"
                    file_blocks.append(f"Context from attached file `{fname}` ({lines} lines):\n```{ext}\n{content}\n```")
                prompt_to_send = "\n\n".join(file_blocks) + f"\n\nTask: {prompt_to_send}"

            # Set up SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_cors_headers()
            self.end_headers()

            # Stream response chunks to browser
            start_time = time.time()
            full_text = ""
            usage_info = None

            try:
                for chunk in engine.stream_query(prompt_to_send):
                    if chunk.text:
                        full_text += chunk.text
                        data_json = json.dumps({"event": "token", "text": chunk.text})
                        self.wfile.write(f"data: {data_json}\n\n".encode("utf-8"))
                        self.wfile.flush()

                    if getattr(chunk, "usage_metadata", None):
                        usage_info = chunk.usage_metadata

                elapsed = time.time() - start_time
                metrics = f"⏱️ {elapsed:.2f}s | 🤖 {engine.model}"
                if usage_info and getattr(usage_info, "total_token_count", None):
                    metrics += f" | 🔢 Tokens: {usage_info.total_token_count} (Prompt: {usage_info.prompt_token_count}, Output: {usage_info.candidates_token_count})"

                engine.record_exchange(raw_query, full_text, metrics)

                done_json = json.dumps({"event": "done", "metrics": metrics})
                self.wfile.write(f"data: {done_json}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

            except Exception as e:
                err_msg = str(e)
                if "not allowed by policy" in err_msg or "403" in err_msg:
                    err_msg = f"{err_msg} (Model '{engine.model}' restricted by API policy. Try selecting another model in the sidebar.)"
                err_json = json.dumps({"event": "error", "message": err_msg})
                try:
                    self.wfile.write(f"data: {err_json}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass

        else:
            self.send_error(404, "Not Found")

    def _serve_file(self, file_path: Path, content_type: str):
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Failed to read file: {e}")

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))
        return {}

    def _send_json(self, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_error(self, message: str):
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

def find_open_port(start_port: int = 8080, max_attempts: int = 10) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def run_server(port: Optional[int] = None, open_browser: bool = True):
    if port is None:
        port = find_open_port(int(os.environ.get("PORT", 8080)))

    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, AetherWebHandler)

    url = f"http://localhost:{port}"
    print("\n" + "═" * 56)
    print("  ⚡ Aether-Link Web Application")
    print(f"  Status:  Online | Model: {engine.model}")
    print(f"  Local:   {url}")
    print("  Press Ctrl + C to stop the server")
    print("═" * 56 + "\n")

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down Aether-Link Web Server... Goodbye.")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()
