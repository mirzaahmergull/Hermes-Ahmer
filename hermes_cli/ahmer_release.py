"""Ahmer's fork uses explicit release promotion, never official self-update."""
from pathlib import Path
import subprocess
import sys

CONTROLLER = Path(r"C:\Hermes-Ahmer\bin\ahmer-release.cmd")


def handle_update(root: Path, args) -> bool:
    if not (root / "Hermes-Ahmer.md").is_file():
        return False
    command = CONTROLLER
    action = "status" if getattr(args, "check", False) or getattr(args, "plan", False) else "deploy"
    if getattr(args, "gateway", False) or not (root.parent / "ahmer-release.json").is_file():
        print("Hermes-Ahmer uses tested fork releases. Run ahmer-release build, then ahmer-release deploy in PowerShell. Official self-update is disabled.")
        return True
    if not command.is_file():
        raise RuntimeError("Hermes-Ahmer release controller is missing; official update remains disabled")
    result = subprocess.run([str(command), action], check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
    return True
