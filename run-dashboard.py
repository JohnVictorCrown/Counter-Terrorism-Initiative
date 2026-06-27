#!/usr/bin/env python3
"""
run-dashboard.py — Start the CRM web dashboard and open it in your browser.

Usage:
    python run-dashboard.py

The Flask server runs on http://localhost:5000.
Press Ctrl+C to stop the server.
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5000
URL = f"http://localhost:{PORT}"

def main():
    print("=" * 55)
    print("  🕵️  CRM Dashboard Launcher")
    print("=" * 55)
    print()
    print(f"  Starting server on {URL} ...")
    print()

    # Start Flask
    server = subprocess.Popen(
        [sys.executable, "-c", 
         f'from app import app; app.run(host="{HOST}", port={PORT}, debug=False)'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=Path(__file__).resolve().parent,
    )

    # Wait for server to start
    time.sleep(2)

    # Check if server is still running
    if server.poll() is not None:
        print("❌ Server failed to start.")
        output = server.stdout.read().decode() if server.stdout else ""
        print(output[:500])
        sys.exit(1)

    # Open browser
    print(f"  ✅ Server is running!")
    print(f"  🌐 Opening {URL} in your browser...")
    webbrowser.open(URL)
    print()
    print("  Press Ctrl+C to stop the server.")
    print()

    try:
        # Stream server output
        for line in server.stdout:
            line = line.decode().strip()
            if line:
                print(f"  {line}")
    except KeyboardInterrupt:
        print()
        print("  Shutting down...")
    finally:
        server.terminate()
        server.wait()
        print("  ✅ Server stopped.")

if __name__ == "__main__":
    main()
