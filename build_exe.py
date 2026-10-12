"""
Windows PyInstaller Executable Packaging Script for FormulaBox Automator
Packages FormulaBox Automator backend and built React frontend into a standalone Windows executable.
"""

import os
import subprocess
import sys

def build_windows_executable():
    print("[1/2] Building React frontend production bundle...")
    frontend_dir = os.path.abspath("frontend")
    result = subprocess.run("npm run build", shell=True, cwd=frontend_dir)
    if result.returncode != 0:
        print("Frontend build failed. Aborting executable packaging.")
        sys.exit(1)

    print("[2/2] Running PyInstaller to package Windows Executable...")
    dist_dir = os.path.join(frontend_dir, "dist")
    
    cmd = [
        "pyinstaller",
        "--name=FormulaBoxAutomator",
        "--onefile",
        "--clean",
        f"--add-data={dist_dir};frontend/dist",
        f"--add-data=backend;backend",
        "run_app.py"
    ]
    
    res = subprocess.run(" ".join(cmd), shell=True)
    if res.returncode == 0:
        print("\nPackaging Success! Standalone executable generated at: dist/FormulaBoxAutomator.exe")
    else:
        print("\nPackaging failed. See log output above.")

if __name__ == "__main__":
    build_windows_executable()
