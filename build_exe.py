import subprocess
import sys

subprocess.run([
    sys.executable,
    "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name=VS-Waage",
    "vs_waage.py"
])