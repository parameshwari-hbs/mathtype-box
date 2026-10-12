import os
import sys
import webbrowser
import time
import socket
import subprocess
import warnings

# Suppress PyMuPDF deprecation warning
warnings.filterwarnings("ignore", message=".*The `fitz` API is deprecated.*")

# Add backend to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from fastapi.staticfiles import StaticFiles
from app.main import app

# Mount static frontend dist directory if available
dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently open and bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def try_free_port(port: int):
    """Attempt to terminate stale processes holding the target port."""
    try:
        cmd = f'netstat -ano | findstr /R /C:":{port} .*LISTENING"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid and pid.isdigit() and int(pid) != os.getpid():
                    print(f"Port {port} is occupied by PID {pid}. Cleaning up stale process...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                    time.sleep(1)
    except Exception as e:
        pass

def get_available_port(start_port: int = 8000, max_tries: int = 20) -> int:
    """Find the next available port, freeing stale processes if necessary."""
    if is_port_in_use(start_port):
        try_free_port(start_port)
    
    for port in range(start_port, start_port + max_tries):
        if not is_port_in_use(port):
            return port
    return start_port

def main():
    print("=" * 60)
    print("      FormulaBox Automator - Standalone Tool")
    print("=" * 60)
    
    port = get_available_port(8000)
    url = f"http://127.0.0.1:{port}"
    print(f"Server starting at {url} ...")
    
    # Open browser automatically after short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()

