# Aether-Link (AetherProject)

[![Status](https://img.shields.io/badge/Status-Online-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#)
[![SDK](https://img.shields.io/badge/SDK-google--genai-orange.svg)](#)
[![Web](https://img.shields.io/badge/Web-Vanilla%20SSE-blue.svg)](#)
[![CLI-UI](https://img.shields.io/badge/UI-Rich-purple.svg)](#)

> **Aether-Link** is a high-level AI research assistant available as both a **modern Web Application** and an **interactive Terminal CLI**. Powered by Google's next-generation Gemini models via the `google-genai` SDK, it provides real-time streaming, dynamic persona switching with persistent memory, local file context injection, and session exportation.

---

## Overview

Aether-Link is engineered to assist developers, researchers, and writers directly within their browser or terminal environments. Built with a shared modular core (`aether_core.py`), you get 100% feature parity whether you prefer the browser interface or the command line.

### Key Capabilities

- **Modern Single-Page Web App**: Zero extra pip dependencies! Runs directly using Python's built-in `ThreadingHTTPServer` with native Server-Sent Events (SSE) for low-latency token streaming.
- **Terminal-Native CLI**: Styled with `rich`, featuring status spinners, Markdown rendering, and custom panels.
- **Real-Time Token Streaming**: Streams responses live token-by-token with formatted Markdown rendering for an instantaneous feedback experience.
- **Dynamic Persona Switcher**: Seamlessly switch between personas (`/coder`, `/writer`, `/researcher`) mid-conversation while retaining conversational memory.
- **File & Code Context Injection**: Directly inject local file contents into your inquiries via browser drag-and-drop / file picker, the `/file <path>` command, or inline `@filename` mentions.
- **Session Export**: Save full multi-turn conversation logs and metadata into formatted Markdown files via `/save [filename]` or the Web App download button.
- **Live Latency & Token Metrics**: Real-time response time and token count tracking displayed under each response.
- **Secure Authentication by Design**: Decouples sensitive API tokens from source control via environment variables or a local `.env` file (conforming to CWE-798 guidelines).

---

## Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core runtime |
| **AI Engine** | [Google GenAI SDK](https://github.com/googleapis/python-genai) (`google-genai`) | Official Gemini API client |
| **Web Server** | Built-in `ThreadingHTTPServer` | Zero-dependency HTTP server with native SSE streaming |
| **Web Frontend** | HTML5, CSS3, JavaScript (ES6) | Responsive Dark Mode UI, marked.js, highlight.js |
| **Terminal UI** | [Rich](https://github.com/Textualize/rich) | CLI formatting, Markdown rendering, panels, spinners |
| **Security** | Standard Environment / `.env` | Credential isolation conforming to CWE-798 guidelines |

---

## Getting Started

### 1. Prerequisites

Ensure you have Python 3.10 or newer installed:

```bash
python3 --version
```

### 2. Installation

Clone the repository and install required dependencies:

```bash
git clone https://github.com/DamilolaAdegunwa/AetherProject.git
cd AetherProject
git checkout web-app
pip install google-genai rich
```

*(Note: The Web Application uses Python's built-in standard library server, requiring zero extra pip packages for the web stack!)*

### 3. API Key Configuration

Aether-Link requires a Gemini API key from Google AI Studio.

1. Generate your API key at [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Configure the key using either of the following methods:

#### Method A: Using a `.env` file (Recommended)

Copy the example configuration file:

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: override default model (default: gemini-3.6-flash)
# GEMINI_MODEL=gemini-3.6-flash
```

#### Method B: Environment Variable

Export the key in your terminal or shell profile (`~/.zshrc` / `~/.bashrc`):

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

> **Security Note:** Never commit `.env` or your API key into git. The repository's `.gitignore` is pre-configured to ignore all `.env` files.

---

## Launching Aether-Link

### 🌐 Option 1: Web Application (Browser)

Launch the web app using the master launcher or directly:

```bash
python3 main.py
# or
python3 aether_web.py
```

The server will launch at `http://localhost:8080` and automatically open your default web browser.

#### Web App Features:
- **Left Sidebar**: One-click persona switcher (🔬 Research Assistant, 💻 Python Coder, ✍️ Creative Novelist).
- **Context Injection**: Drag-and-drop files directly into the browser or click **📂 Attach File** to select project files.
- **Session Management**: Export full conversation logs to Markdown with **💾 Export Session**, or reset history with **🧹 Clear Conversation**.
- **Chat Window**: Real-time token streaming cards with live Markdown rendering, status indicator, elapsed time (⏱️), and token count metrics (🔢).
- **Input Field**: Auto-expanding textarea (Enter to send, Shift+Enter for newline). All slash commands and `@filename` mentions work directly in the web chat input!

---

### 💻 Option 2: Terminal Assistant (CLI)

Launch the terminal version:

```bash
python3 main.py --cli
# or
python3 aether_link.py
```

#### Supported Commands in Web & CLI:
 
| Command / Action | Web Equivalent | Role & Description |
| :--- | :--- | :--- |
| `/coder` | Click **💻 Python Programmer** | Switch persona to `"You are an expert Python programmer."` |
| `/writer` | Click **✍️ Creative Novelist** | Switch persona to `"You are a creative novelist."` |
| `/researcher`, `/default` | Click **🔬 Research Assistant** | Switch back to `"You are Aether-Link, a high-level research assistant."` |
| `/file <path> [prompt]` | Drag file / Click **📂 Attach** | Injects local file content into the prompt context |
| `@<filepath>` | Type `@filename` in prompt | Automatically attaches local file mentioned anywhere in prompt |
| `/save [filename]` | Click **💾 Export Session** | Exports current chat transcript to a Markdown file |
| `/clear` | Click **🧹 Clear Conversation** | Resets conversation memory and starts a fresh session |
| `/personas`, `/help` | Sidebar Persona Menu | Displays formatted table of all personas and commands |
| `exit`, `quit`, `/exit` | Close Browser Tab | Cleanly terminates the session |

---

## REST API Documentation

The web server includes built-in endpoints for programmatic integration:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the single-page application |
| `/api/status` | `GET` | Returns online status, active persona, model, and exchange count |
| `/api/personas` | `GET` | Returns all available personas and current active selection |
| `/api/persona` | `POST` | Switches persona: `{"persona": "coder"}` |
| `/api/model` | `POST` | Switches model: `{"model": "gemini-3.6-flash"}` |
| `/api/chat` | `POST` | Server-Sent Events (SSE) streaming endpoint for inquiries |
| `/api/clear` | `POST` | Resets conversation memory |
| `/api/export` | `GET` | Downloads session log as a Markdown attachment |

---

## Project Structure

```text
AetherProject/
├── .env.example       # Template for environment configuration
├── .gitignore          # Excludes secrets, credentials, and cache files
├── aether_core.py     # Shared engine: Gemini client, personas, file parser, streaming
├── aether_web.py      # Zero-dependency HTTP server with SSE streaming & REST API
├── aether_link.py     # Terminal assistant client (Rich CLI)
├── main.py            # Master launcher (Web App default, --cli for terminal)
├── static/            # Web frontend assets
│   ├── index.html     # Single-page web application
│   ├── style.css      # Dark-themed stylesheet
│   └── app.js         # Client-side streaming, upload, and persona logic
└── README.md          # Project documentation
```

---

## License

This project is licensed under the MIT License - see the repository for details.
