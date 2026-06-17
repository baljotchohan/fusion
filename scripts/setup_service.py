#!/usr/bin/env python3
# scripts/setup_service.py
"""
Setup FUSION MCP backend as an always-on macOS background service (LaunchAgent).
Allows Claude Code (and other MCP clients) to always connect automatically.
"""
import os
import sys
import subprocess
import time
import socket

LABEL = "com.fusion.backend"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")


def port_is_open(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


def main():
    print("⚖️ Setting up FUSION as an always-on macOS background service...")

    # Resolve paths
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    run_py = os.path.join(repo_root, "run.py")

    # Locate virtualenv python
    venv_python = os.path.join(repo_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        print(f"Warning: Virtual env python not found at {venv_python}. Using fallback: {sys.executable}")
        venv_python = sys.executable

    # Construct the launch agent plist content
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>{run_py}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>BAND_MOCK</key>
        <string>true</string>
        <key>PORT</key>
        <string>8000</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{repo_root}</string>
    <key>StandardOutPath</key>
    <string>{os.path.join(repo_root, "server.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.join(repo_root, "server.log")}</string>
</dict>
</plist>
"""

    # Ensure LaunchAgents directory exists
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)

    # Write plist file
    with open(PLIST_PATH, "w") as f:
        f.write(plist_content)
    print(f"✓ Created launch agent configuration at {PLIST_PATH}")

    # Unload if already loaded
    try:
        subprocess.run(["launchctl", "unload", PLIST_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Load and start the background service
    print("⌛ Starting the FUSION background service via launchctl...")
    res = subprocess.run(["launchctl", "load", PLIST_PATH], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error loading launch agent: {res.stderr.strip()}")
        sys.exit(1)

    # Wait for the service to start up and open port 8000
    print("⌛ Waiting for port 8000 to become active...")
    for _ in range(10):
        if port_is_open(8000):
            break
        time.sleep(1)

    if not port_is_open(8000):
        print("❌ Error: FUSION backend failed to start on port 8000. Check server.log for errors.")
        sys.exit(1)

    print("✓ FUSION background service is running on port 8000.")

    # Automatically register with Claude Code
    print("⌛ Registering fusion MCP server with Claude Code...")
    # Remove existing 'fusion' to avoid conflicts
    subprocess.run(["claude", "mcp", "remove", "fusion"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Add new one
    mcp_add_cmd = ["claude", "mcp", "add", "--transport", "http", "fusion", "http://localhost:8000/mcp/"]
    res = subprocess.run(mcp_add_cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("✓ Successfully configured Claude Code to connect to local FUSION MCP server.")
    else:
        print(f"Warning: Could not configure Claude Code automatically: {res.stderr.strip()}")
        print("You can add it manually by running:")
        print("  claude mcp add --transport http fusion http://localhost:8000/mcp/")

    print("\n🎉 Done! FUSION MCP is now always-on and will launch automatically when your Mac boots.")
    print("To stop the service at any time, run:")
    print(f"  launchctl unload {PLIST_PATH}")
    print("To restart/start it again, run:")
    print(f"  launchctl load {PLIST_PATH}")


if __name__ == "__main__":
    main()
