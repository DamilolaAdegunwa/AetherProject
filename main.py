#!/usr/bin/env python3
"""
Aether-Link Master Launcher
Run without arguments to launch the Web Application:
    python3 main.py

Or pass --cli to launch the terminal interface:
    python3 main.py --cli
"""
import sys

def main():
    if "--cli" in sys.argv:
        from aether_link import AetherLinkCLI
        app = AetherLinkCLI()
        app.run()
    else:
        from aether_web import run_server
        # Default to web app and open browser
        run_server(open_browser=True)

if __name__ == "__main__":
    main()
