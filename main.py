#!/usr/bin/env python3
"""
Aether-Link Master Launcher
Run without arguments to launch the Desktop GUI:
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
        try:
            from aether_gui import AetherLinkGUI
            app = AetherLinkGUI()
            app.mainloop()
        except Exception as e:
            print(f"Failed to start Desktop GUI: {e}")
            print("Falling back to Terminal CLI...\n")
            from aether_link import AetherLinkCLI
            app = AetherLinkCLI()
            app.run()

if __name__ == "__main__":
    main()
