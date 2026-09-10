# Aether-Link (AetherProject)

[![Status](https://img.shields.io/badge/Status-Online-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#)
[![SDK](https://img.shields.io/badge/SDK-google--genai-orange.svg)](#)
[![CLI-UI](https://img.shields.io/badge/UI-Rich-purple.svg)](#)

> **Aether-Link** is a terminal-native, high-level research assistant designed to provide expert technical advice, deep analytical reasoning, and seamless conversational memory directly within developer workflows.

---

## Overview

Aether-Link bridges the gap between state-of-the-art generative intelligence and the command line. Built with Google's next-generation `google-genai` SDK and styled with `rich`, Aether-Link provides a responsive, beautifully formatted terminal interface for pair-programming, vulnerability analysis, architecture reviews, and high-level technical research.

### Key Capabilities

- **Real-Time Token Streaming**: Streams responses live token-by-token with formatted Markdown rendering for an instantaneous feedback experience.
- **Dynamic Persona Switcher**: Seamlessly switch between personas (`/coder`, `/writer`, `/researcher`) mid-conversation while retaining memory context.
- **File & Code Context Injection**: Directly inject local file contents into your inquiries using `/file <path>` or inline `@filename` mentions.
- **Session Export**: Save full multi-turn conversation logs and metadata into formatted Markdown files via `/save [filename]`.
- **Live Latency & Token Metrics**: Real-time response time and token count tracking displayed under each response.
- **Multi-Turn Conversational Memory**: Native Gemini Chat sessions keep full conversational context across consecutive queries.
- **Secure Authentication by Design**: Decouples sensitive API tokens from source control via environment variables or a local `.env` file.

---

## Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core runtime |
| **AI Engine** | [Google GenAI SDK](https://github.com/googleapis/python-genai) (`google-genai`) | Official Gemini API client |
| **Terminal UI** | [Rich](https://github.com/Textualize/rich) | Terminal formatting, Markdown rendering, panels, spinners |
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
pip install google-genai rich
```

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
# Optional: override default model
# GEMINI_MODEL=gemini-2.5-flash
```

#### Method B: Environment Variable

Export the key in your terminal or shell profile (`~/.zshrc` / `~/.bashrc`):

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

> **Security Note:** Never commit `.env` or your API key into git. The repository's `.gitignore` is pre-configured to ignore all `.env` files.

---

## Usage

Launch the assistant by running:

```bash
python3 aether_link.py
```

### Example Session

```text
╭─────────────────────────────────╮
│ Aether-Link Terminal v1.0       │
│ Status: Online | Memory: Active │
╰─────────────────────────────────╯

Query: Explain the difference between symmetric and asymmetric encryption

Gemini is thinking...

Aether-Link System Response:
────────────────────────────────────────
### Symmetric vs. Asymmetric Encryption

| Feature | Symmetric Encryption | Asymmetric Encryption |
| :--- | :--- | :--- |
| **Key Usage** | Single shared secret key | Key pair (Public & Private keys) |
| **Speed** | Extremely fast (hardware-accelerated) | Slower (mathematically intensive) |
| **Use Cases** | Bulk data encryption (AES-256, ChaCha20) | Key exchange, Digital signatures (RSA, ECC) |
────────────────────────────────────────

Query: quit
Shutting down Aether-Link... Goodbye.
```

### Supported Commands & Features
 
| Command | Action | Description |
| :--- | :--- | :--- |
| `/coder` | 💻 **Expert Python Programmer** | Switch persona to `"You are an expert Python programmer."` |
| `/writer` | ✍️ **Creative Novelist** | Switch persona to `"You are a creative novelist."` |
| `/researcher`, `/default` | 🔬 **Research Assistant** | Switch back to `"You are Aether-Link, a high-level research assistant."` |
| `/file <path> [prompt]` | 📂 **File Context** | Injects local file content into the prompt context |
| `@<filepath>` | 🏷️ **Inline File Mention** | Automatically loads `@filename` mentioned anywhere in your prompt |
| `/save [filename]` | 💾 **Export Session** | Exports the current chat transcript to Markdown in `saved_sessions/` |
| `/personas`, `/help` | 📋 **Help Menu** | Displays formatted table of all personas and commands |
| `/clear` | 🧹 **Memory Reset** | Resets conversation memory and starts a fresh session |
| `exit`, `quit`, `/exit` | 🚪 **Shutdown** | Cleanly terminates the Aether-Link session |

---

## Project Structure

```text
AetherProject/
├── .env.example       # Template for environment configuration
├── .gitignore          # Excludes secrets, credentials, and cache files
├── aether_link.py     # Main terminal assistant client
└── README.md          # Project documentation
```

---

## License

This project is licensed under the MIT License - see the repository for details.
