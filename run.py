"""
Healthcare Chatbot - Unified Runner
Runs both Flask web server and LiveKit voice agent together
"""

import subprocess
import sys
import os
import time
import signal
from threading import Thread

# Change to project directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

processes = []

def run_flask():
    """Run Flask web server"""
    print("\n[FLASK] Starting web server on http://localhost:5000")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(proc)

    for line in proc.stdout:
        print(f"[FLASK] {line}", end="")

def run_voice_agent():
    """Run LiveKit voice agent"""
    time.sleep(2)  # Wait for Flask to start first
    print("\n[VOICE] Starting voice agent...")
    proc = subprocess.Popen(
        [sys.executable, "voice_agent.py", "dev"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(proc)

    for line in proc.stdout:
        print(f"[VOICE] {line}", end="")

def cleanup(signum=None, frame=None):
    """Clean up all processes on exit"""
    print("\n\nShutting down...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == "__main__":
    print("=" * 50)
    print("  Healthcare Chatbot - Starting All Services")
    print("=" * 50)
    print("\nServices:")
    print("  - Web Server: http://localhost:5000")
    print("  - Voice Agent: LiveKit Connected")
    print("\nPress Ctrl+C to stop all services")
    print("=" * 50)

    # Start Flask in main thread, voice agent in background
    flask_thread = Thread(target=run_flask, daemon=True)
    voice_thread = Thread(target=run_voice_agent, daemon=True)

    flask_thread.start()
    voice_thread.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
