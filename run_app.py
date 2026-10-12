import os
import sys
import webbrowser
import time
import socket
import subprocess
import warnings

import shutil

# Suppress PyMuPDF deprecation warning
warnings.filterwarnings("ignore", message=".*The `fitz` API is deprecated.*")

# Dynamically resolve project root directory (supports PyInstaller frozen executable)
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

backend_dir = os.path.join(PROJECT_ROOT, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from app.main import app

def ensure_frontend_built() -> str:
    """Dynamically builds the React frontend if dist/index.html is missing."""
    dist_dir = os.path.join(PROJECT_ROOT, "frontend", "dist")
    index_html = os.path.join(dist_dir, "index.html")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

    if getattr(sys, 'frozen', False) or os.path.exists(index_html):
        return dist_dir

    print("=" * 60)
    print("Frontend production bundle not found. Building dynamically...")
    print("=" * 60)

    npm_cmd = shutil.which("npm") or ("npm.cmd" if sys.platform == "win32" else "npm")
    node_modules = os.path.join(frontend_dir, "node_modules")

    if not os.path.exists(node_modules):
        try:
            print("[*] Installing frontend dependencies (npm install)...")
            subprocess.run(f"{npm_cmd} install", shell=True, cwd=frontend_dir, check=True)
        except Exception as e:
            print(f"[!] Warning: npm install failed: {e}")

    try:
        print("[*] Compiling frontend bundle (npm run build)...")
        subprocess.run(f"{npm_cmd} run build", shell=True, cwd=frontend_dir, check=True)
        print("[+] Frontend bundle compiled successfully!")
    except Exception as e:
        print(f"[!] Warning: npm run build could not be executed: {e}")

    return dist_dir

dist_dir = ensure_frontend_built()

# Mount static assets directory if available
assets_dir = os.path.join(dist_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# SPA catch-all handler for dynamic routing and fallback
@app.get("/{full_path:path}")
async def serve_spa_app(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    target_file = os.path.join(dist_dir, full_path)
    if full_path and os.path.isfile(target_file):
        return FileResponse(target_file)

    index_file = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FormulaBox Automator - Setup</title>
            <style>
                body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .box { max-width: 520px; padding: 2.5rem; background: #1e293b; border-radius: 1rem; border: 1px solid #334155; text-align: center; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
                h1 { color: #f43f5e; margin-top: 0; }
                p { color: #94a3b8; line-height: 1.6; font-size: 0.95rem; }
                code { background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 0.35rem; color: #38bdf8; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>FormulaBox Automator</h1>
                <p>Frontend production bundle is not yet compiled on this machine.</p>
                <p>Please open a terminal and run:<br><br><code>cd frontend && npm install && npm run build</code></p>
                <p>Then refresh this browser window.</p>
            </div>
        </body>
        </html>
        """,
        status_code=200
    )

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

