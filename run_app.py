"""
FormulaBox Automator - Standalone Launcher
Starts the Python backend server and opens the web application in the browser.
"""

import os
import sys
import webbrowser
import time
import uvicorn
from fastapi.staticfiles import StaticFiles

# Add backend to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Mount static frontend dist directory if available
dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

def main():
    print("=" * 60)
    print("      FormulaBox Automator - Standalone Tool")
    print("=" * 60)
    print("Server starting at http://127.0.0.1:8000 ...")
    
    # Open browser automatically after short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
