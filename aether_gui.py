import os
import sys
import time
import queue
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, Tuple

from aether_core import (
    PERSONAS,
    process_file_context,
    AetherEngine,
    DEFAULT_MODEL,
    load_dotenv
)

# Ensure .env is loaded
load_dotenv()

# Color Palette (Modern Dark Theme)
BG_DARK = "#121417"
BG_SIDEBAR = "#181B20"
BG_CARD_USER = "#1E314B"
BG_CARD_BOT = "#1C212B"
BG_INPUT = "#222733"
TEXT_PRIMARY = "#ECEFF4"
TEXT_SECONDARY = "#9AA5B8"
TEXT_MUTED = "#6C7A90"
ACCENT_BLUE = "#3B82F6"
ACCENT_GREEN = "#10B981"
ACCENT_PURPLE = "#8B5CF6"
ACCENT_RED = "#EF4444"
BORDER_COLOR = "#2A313E"

class AetherLinkGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Aether-Link Terminal — Desktop Edition")
        self.geometry("1100;750".replace(";", "x"))
        self.minsize(850, 600)
        self.configure(bg=BG_DARK)

        # Initialize Core Engine
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            messagebox.showerror(
                "API Key Missing",
                "GEMINI_API_KEY environment variable is not set.\n\n"
                "Please configure it in a .env file or export it before launching."
            )
            self.destroy()
            sys.exit(1)

        try:
            self.engine = AetherEngine(api_key=api_key, model=DEFAULT_MODEL)
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize Gemini engine:\n{e}")
            self.destroy()
            sys.exit(1)

        # State management
        self.attached_files: List[Tuple[str, int]] = []
        self.is_generating = False
        self.stop_requested = False
        self.stream_queue = queue.Queue()
        self.current_stream_id = 0

        # Build UI
        self._setup_styles()
        self._build_layout()
        self._bind_shortcuts()

        # Start queue polling loop for thread-safe streaming
        self.after(50, self._process_stream_queue)

        # Welcome message
        self._append_system_message(
            f"✨ Welcome to Aether-Link Desktop v1.0\n"
            f"Active Persona: {PERSONAS[self.engine.active_persona]['name']} {PERSONAS[self.engine.active_persona]['icon']}\n"
            f"Model: {self.engine.model} | Memory: Active"
        )

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
        style.configure("Main.TFrame", background=BG_DARK)
        style.configure("Card.TFrame", background=BG_CARD_BOT, relief="flat")
        style.configure("Status.TLabel", background=BG_SIDEBAR, foreground=TEXT_SECONDARY, font=("Helvetica", 10))

    def _build_layout(self):
        # Master horizontal container
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BORDER_COLOR, bd=0, sashwidth=2)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # --- LEFT SIDEBAR ---
        self.sidebar = tk.Frame(self.paned, bg=BG_SIDEBAR, width=280)
        self.sidebar.pack_propagate(False)
        self.paned.add(self.sidebar, minsize=240)

        self._build_sidebar()

        # --- RIGHT CHAT AREA ---
        self.main_area = tk.Frame(self.paned, bg=BG_DARK)
        self.paned.add(self.main_area, minsize=550)

        self._build_main_area()

    def _build_sidebar(self):
        # Branding Header
        header_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, pady=16, padx=16)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="⚡ Aether-Link",
            font=("Helvetica", 16, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_SIDEBAR
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame,
            text="High-Level AI Assistant",
            font=("Helvetica", 10),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Status badge
        self.status_badge = tk.Label(
            header_frame,
            text="● Online",
            font=("Helvetica", 9, "bold"),
            fg=ACCENT_GREEN,
            bg=BG_SIDEBAR
        )
        self.status_badge.pack(anchor="w", pady=(6, 0))

        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=12, pady=8)

        # Persona Selector Section
        persona_section = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=6)
        persona_section.pack(fill=tk.X)

        tk.Label(
            persona_section,
            text="ASSISTANT PERSONA",
            font=("Helvetica", 9, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 8))

        self.persona_var = tk.StringVar(value=self.engine.active_persona)
        self.persona_buttons = {}

        for key, p in PERSONAS.items():
            btn = tk.Button(
                persona_section,
                text=f"{p['icon']}  {p['name']}",
                font=("Helvetica", 11),
                anchor="w",
                padx=12,
                pady=8,
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda k=key: self._on_select_persona(k)
            )
            btn.pack(fill=tk.X, pady=3)
            self.persona_buttons[key] = btn

        self._refresh_persona_button_styles()

        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=12, pady=12)

        # File Context Section
        file_section = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=4)
        file_section.pack(fill=tk.X)

        tk.Label(
            file_section,
            text="CONTEXT INJECTION",
            font=("Helvetica", 9, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 8))

        attach_btn = tk.Button(
            file_section,
            text="📂  Attach File Context",
            font=("Helvetica", 10, "bold"),
            bg="#27303F",
            fg=TEXT_PRIMARY,
            activebackground="#334055",
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=7,
            command=self._on_attach_file_dialog
        )
        attach_btn.pack(fill=tk.X, pady=(0, 6))

        # Attached files container
        self.attached_frame = tk.Frame(file_section, bg=BG_SIDEBAR)
        self.attached_frame.pack(fill=tk.X)

        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=12, pady=12)

        # Quick Actions Section
        action_section = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=4)
        action_section.pack(fill=tk.X)

        tk.Label(
            action_section,
            text="SESSION ACTIONS",
            font=("Helvetica", 9, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 8))

        save_btn = tk.Button(
            action_section,
            text="💾  Export Session (.md)",
            font=("Helvetica", 10),
            bg=BG_SIDEBAR,
            fg=TEXT_SECONDARY,
            activebackground="#252A35",
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=1,
            highlightbackground=BORDER_COLOR,
            cursor="hand2",
            padx=10,
            pady=6,
            anchor="w",
            command=self._on_export_session
        )
        save_btn.pack(fill=tk.X, pady=3)

        clear_btn = tk.Button(
            action_section,
            text="🧹  Clear Conversation",
            font=("Helvetica", 10),
            bg=BG_SIDEBAR,
            fg=TEXT_SECONDARY,
            activebackground="#252A35",
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=1,
            highlightbackground=BORDER_COLOR,
            cursor="hand2",
            padx=10,
            pady=6,
            anchor="w",
            command=self._on_clear_chat
        )
        clear_btn.pack(fill=tk.X, pady=3)

        # Bottom Model Selector
        footer = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=16)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(
            footer,
            text="GEMINI MODEL",
            font=("Helvetica", 9, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 4))

        self.model_var = tk.StringVar(value=self.engine.model)
        self.model_dropdown = ttk.Combobox(
            footer,
            textvariable=self.model_var,
            values=["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            state="readonly",
            font=("Helvetica", 10)
        )
        self.model_dropdown.pack(fill=tk.X, pady=(0, 4))
        self.model_dropdown.bind("<<ComboboxSelected>>", self._on_model_selected)

    def _build_main_area(self):
        # Header bar
        header = tk.Frame(self.main_area, bg=BG_DARK, height=52, padx=20, pady=10)
        header.pack(fill=tk.X)

        self.chat_title_lbl = tk.Label(
            header,
            text=f"{PERSONAS[self.engine.active_persona]['icon']}  {PERSONAS[self.engine.active_persona]['name']}",
            font=("Helvetica", 13, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_DARK
        )
        self.chat_title_lbl.pack(side=tk.LEFT)

        self.header_metric_lbl = tk.Label(
            header,
            text="",
            font=("Helvetica", 10),
            fg=TEXT_MUTED,
            bg=BG_DARK
        )
        self.header_metric_lbl.pack(side=tk.RIGHT)

        tk.Frame(self.main_area, bg=BORDER_COLOR, height=1).pack(fill=tk.X)

        # Chat Transcript (Scrollable Text with Custom Tags)
        chat_container = tk.Frame(self.main_area, bg=BG_DARK)
        chat_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        self.chat_scroll = ttk.Scrollbar(chat_container)
        self.chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_text = tk.Text(
            chat_container,
            bg=BG_DARK,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            wrap=tk.WORD,
            font=("Helvetica", 12),
            padx=16,
            pady=12,
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.chat_scroll.set
        )
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.chat_scroll.config(command=self.chat_text.yview)

        # Text styles & formatting tags
        self.chat_text.tag_configure("system", foreground=ACCENT_PURPLE, font=("Helvetica", 10, "italic"), justify="center")
        self.chat_text.tag_configure("user_header", foreground=ACCENT_BLUE, font=("Helvetica", 11, "bold"), lmargin1=10, lmargin2=10)
        self.chat_text.tag_configure("user_body", foreground=TEXT_PRIMARY, font=("Helvetica", 12), lmargin1=15, lmargin2=15)
        self.chat_text.tag_configure("bot_header", foreground=ACCENT_GREEN, font=("Helvetica", 11, "bold"), lmargin1=10, lmargin2=10)
        self.chat_text.tag_configure("bot_body", foreground=TEXT_PRIMARY, font=("Helvetica", 12), lmargin1=15, lmargin2=15)
        self.chat_text.tag_configure("code_block", foreground="#A3E635", background="#171A21", font=("Courier", 11), lmargin1=25, lmargin2=25)
        self.chat_text.tag_configure("metrics", foreground=TEXT_MUTED, font=("Helvetica", 9), lmargin1=15, lmargin2=15)
        self.chat_text.tag_configure("divider", foreground=BORDER_COLOR)

        self.chat_text.config(state=tk.DISABLED)

        # --- BOTTOM INPUT AREA ---
        input_container = tk.Frame(self.main_area, bg=BG_DARK, padx=16, pady=12)
        input_container.pack(fill=tk.X)

        input_box_frame = tk.Frame(input_container, bg=BG_INPUT, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR)
        input_box_frame.pack(fill=tk.X)

        self.input_text = tk.Text(
            input_box_frame,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            wrap=tk.WORD,
            font=("Helvetica", 12),
            height=3,
            padx=12,
            pady=10,
            bd=0,
            highlightthickness=0
        )
        self.input_text.pack(fill=tk.X, expand=True)

        # Action row below input
        action_row = tk.Frame(input_box_frame, bg=BG_INPUT, padx=8, pady=6)
        action_row.pack(fill=tk.X)

        self.file_quick_btn = tk.Button(
            action_row,
            text="📎 Attach File",
            font=("Helvetica", 9),
            bg=BG_INPUT,
            fg=TEXT_SECONDARY,
            activebackground="#2A313E",
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._on_attach_file_dialog
        )
        self.file_quick_btn.pack(side=tk.LEFT)

        self.hint_lbl = tk.Label(
            action_row,
            text="Press Enter to send (Shift+Enter for newline) | Slash commands supported",
            font=("Helvetica", 9),
            fg=TEXT_MUTED,
            bg=BG_INPUT
        )
        self.hint_lbl.pack(side=tk.LEFT, padx=12)

        self.send_btn = tk.Button(
            action_row,
            text="➤  Send",
            font=("Helvetica", 10, "bold"),
            bg=ACCENT_BLUE,
            fg="#FFFFFF",
            activebackground="#2563EB",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=4,
            command=self._on_send_click
        )
        self.send_btn.pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        self.input_text.bind("<Return>", self._on_enter_pressed)
        self.input_text.bind("<Shift-Return>", lambda e: None)  # Allow newline
        self.bind("<Escape>", lambda e: self._on_stop_click())

    def _on_model_selected(self, event=None):
        new_model = self.model_var.get()
        if new_model != self.engine.model:
            self.engine.set_model(new_model)
            self._append_system_message(f"🤖 Model switched to: {new_model}")

    def _refresh_persona_button_styles(self):
        active = self.engine.active_persona
        for key, btn in self.persona_buttons.items():
            if key == active:
                btn.config(bg=ACCENT_PURPLE, fg="#FFFFFF", font=("Helvetica", 11, "bold"))
            else:
                btn.config(bg=BG_SIDEBAR, fg=TEXT_SECONDARY, font=("Helvetica", 11))

    def _on_select_persona(self, key: str):
        if key == self.engine.active_persona:
            return

        if self.engine.set_persona(key):
            self._refresh_persona_button_styles()
            p = PERSONAS[key]
            self.chat_title_lbl.config(text=f"{p['icon']}  {p['name']}")
            self._append_system_message(
                f"🔄 Persona switched to: {p['name']} {p['icon']}\n\"{self.engine.system_instruction}\""
            )

    def _on_attach_file_dialog(self):
        chosen = filedialog.askopenfilename(
            title="Select File for Context Injection",
            filetypes=[("Text & Code Files", "*.py *.md *.txt *.json *.js *.ts *.html *.css *.yaml *.yml *.env.example *.sh *.c *.cpp *.rs *.go"), ("All Files", "*.*")]
        )
        if not chosen:
            return

        p = Path(chosen)
        rel_path = str(p.name)
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = len(content.splitlines())
            self.attached_files.append((chosen, lines))
            self._render_attached_file_pills()
        except Exception as e:
            messagebox.showerror("File Error", f"Could not read file:\n{e}")

    def _render_attached_file_pills(self):
        for widget in self.attached_frame.winfo_children():
            widget.destroy()

        for idx, (path_str, lines) in enumerate(self.attached_files):
            p = Path(path_str)
            pill = tk.Frame(self.attached_frame, bg="#212733", bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
            pill.pack(fill=tk.X, pady=2)

            name_lbl = tk.Label(
                pill,
                text=f"📄 {p.name} ({lines}L)",
                font=("Helvetica", 9),
                fg=TEXT_PRIMARY,
                bg="#212733"
            )
            name_lbl.pack(side=tk.LEFT, padx=6, pady=2)

            del_btn = tk.Button(
                pill,
                text="✕",
                font=("Helvetica", 8, "bold"),
                fg=ACCENT_RED,
                bg="#212733",
                bd=0,
                cursor="hand2",
                command=lambda i=idx: self._remove_attached_file(i)
            )
            del_btn.pack(side=tk.RIGHT, padx=4)

    def _remove_attached_file(self, index: int):
        if 0 <= index < len(self.attached_files):
            self.attached_files.pop(index)
            self._render_attached_file_pills()

    def _on_export_session(self):
        if not self.engine.session_log:
            messagebox.showinfo("Export Session", "No conversation history to export yet.")
            return

        suggested_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        target = filedialog.asksaveasfilename(
            title="Export Session to Markdown",
            initialdir="saved_sessions",
            initialfile=suggested_name,
            defaultextension=".md",
            filetypes=[("Markdown Document", "*.md"), ("All Files", "*.*")]
        )
        if not target:
            return

        try:
            saved_path = self.engine.export_session_to_markdown(Path(target))
            messagebox.showinfo("Session Exported", f"Successfully saved session transcript to:\n{saved_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to save session:\n{e}")

    def _on_clear_chat(self):
        if not self.engine.session_log:
            return

        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear conversation memory and chat log?"):
            self.engine.clear_history()
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete("1.0", tk.END)
            self.chat_text.config(state=tk.DISABLED)
            self.attached_files.clear()
            self._render_attached_file_pills()
            self._append_system_message("🧹 Conversation memory cleared. Fresh session started.")

    def _on_enter_pressed(self, event):
        # If Shift was held, let it insert newline
        if event.state & 0x0001:
            return None
        self._on_send_click()
        return "break"

    def _on_send_click(self):
        if self.is_generating:
            self._on_stop_click()
            return

        user_raw = self.input_text.get("1.0", tk.END).strip()
        if not user_raw:
            return

        # Clear input box
        self.input_text.delete("1.0", tk.END)

        # Handle slash commands in GUI input
        cmd_lower = user_raw.lower()
        if cmd_lower == "/coder":
            self._on_select_persona("coder")
            return
        elif cmd_lower == "/writer":
            self._on_select_persona("writer")
            return
        elif cmd_lower in ["/researcher", "/default"]:
            self._on_select_persona("researcher")
            return
        elif cmd_lower == "/clear":
            self._on_clear_chat()
            return
        elif cmd_lower.startswith("/save"):
            self._on_export_session()
            return
        elif cmd_lower in ["exit", "quit", "/exit", "/quit"]:
            self.destroy()
            return

        # Build prompt incorporating attached files and @mentions
        prompt_to_send, loaded_from_mentions, err = process_file_context(user_raw)
        if err:
            messagebox.showerror("Context Error", err)
            return

        # Append manually attached files from sidebar if any
        if self.attached_files:
            file_blocks = []
            for path_str, lines in self.attached_files:
                p = Path(path_str)
                ext = p.suffix.lstrip(".") or "text"
                content = p.read_text(encoding="utf-8", errors="replace")
                file_blocks.append(f"Context from attached file `{p.name}` ({lines} lines):\n```{ext}\n{content}\n```")
            
            prompt_to_send = "\n\n".join(file_blocks) + f"\n\nTask: {prompt_to_send}"
            # Clear manual attachments after sending
            self.attached_files.clear()
            self._render_attached_file_pills()

        # Display user message in chat
        self._append_user_message(user_raw)

        # Start streaming in worker thread
        self._start_streaming_response(user_raw, prompt_to_send)

    def _on_stop_click(self):
        if self.is_generating:
            self.stop_requested = True
            self.stream_queue.put(("status", "Generation interrupted by user."))

    def _append_system_message(self, text: str):
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"\n{text}\n\n", "system")
        self.chat_text.insert(tk.END, "─" * 60 + "\n\n", "divider")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def _append_user_message(self, text: str):
        self.chat_text.config(state=tk.NORMAL)
        time_str = datetime.now().strftime("%H:%M:%S")
        self.chat_text.insert(tk.END, f"👤 You ({time_str})\n", "user_header")
        self.chat_text.insert(tk.END, f"{text}\n\n", "user_body")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def _start_streaming_response(self, original_query: str, prompt_to_send: str):
        self.is_generating = True
        self.stop_requested = False
        self.current_stream_id += 1
        stream_id = self.current_stream_id

        # Switch send button to stop button
        self.send_btn.config(text="⏹  Stop", bg=ACCENT_RED, activebackground="#DC2626")
        self.status_badge.config(text="● Thinking...", fg=ACCENT_PURPLE)

        # Prepare chat header for bot response
        active_p = PERSONAS[self.engine.active_persona]
        time_str = datetime.now().strftime("%H:%M:%S")

        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"{active_p['icon']} {active_p['name']} ({time_str})\n", "bot_header")
        self.current_bot_text_start = self.chat_text.index(tk.END)
        self.chat_text.config(state=tk.DISABLED)

        # Run streaming in background daemon thread
        threading.Thread(
            target=self._worker_stream_gemini,
            args=(stream_id, original_query, prompt_to_send),
            daemon=True
        ).start()

    def _worker_stream_gemini(self, stream_id: int, original_query: str, prompt_to_send: str):
        start_time = time.time()
        full_text = ""
        usage_info = None

        try:
            for chunk in self.engine.stream_query(prompt_to_send):
                if self.stop_requested or stream_id != self.current_stream_id:
                    break

                if chunk.text:
                    full_text += chunk.text
                    self.stream_queue.put(("chunk", chunk.text))

                if getattr(chunk, "usage_metadata", None):
                    usage_info = chunk.usage_metadata

            elapsed = time.time() - start_time
            metrics = f"⏱️ {elapsed:.2f}s | 🤖 {self.engine.model}"
            if usage_info and getattr(usage_info, "total_token_count", None):
                metrics += f" | 🔢 Tokens: {usage_info.total_token_count} (Prompt: {usage_info.prompt_token_count}, Output: {usage_info.candidates_token_count})"

            # Record exchange in core engine
            self.engine.record_exchange(original_query, full_text, metrics)
            self.stream_queue.put(("done", metrics))

        except Exception as e:
            err_msg = str(e)
            if "not allowed by policy" in err_msg or "403" in err_msg:
                err_msg = f"{err_msg}\n\n💡 Tip: The model '{self.engine.model}' is restricted by API policy. Try selecting another model (e.g. 'gemini-3.6-flash') from the model selector dropdown in the sidebar."
            self.stream_queue.put(("error", err_msg))

    def _process_stream_queue(self):
        """Poll worker thread events on the main Tkinter thread."""
        try:
            while True:
                event, payload = self.stream_queue.get_nowait()

                if event == "chunk":
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, payload, "bot_body")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)

                elif event == "done":
                    metrics = payload
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, f"\n\n{metrics}\n", "metrics")
                    self.chat_text.insert(tk.END, "─" * 60 + "\n\n", "divider")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)

                    self.header_metric_lbl.config(text=metrics)
                    self._reset_input_state()

                elif event == "status":
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, f"\n[ {payload} ]\n", "metrics")
                    self.chat_text.insert(tk.END, "─" * 60 + "\n\n", "divider")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)
                    self._reset_input_state()

                elif event == "error":
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, f"\n[Error: {payload}]\n\n", "system")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)
                    self._reset_input_state()

        except queue.Empty:
            pass

        # Schedule next check
        self.after(30, self._process_stream_queue)

    def _reset_input_state(self):
        self.is_generating = False
        self.stop_requested = False
        self.send_btn.config(text="➤  Send", bg=ACCENT_BLUE, activebackground="#2563EB")
        self.status_badge.config(text="● Online", fg=ACCENT_GREEN)

if __name__ == "__main__":
    app = AetherLinkGUI()
    app.mainloop()
