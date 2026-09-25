"""Windows opt-in for PSF-signed Python and TLS binaries.

This verifies selected native binaries and a working SSL import, not the integrity
of every stdlib or site-packages file. Install Python from the official PSF
installer before opting in.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from pm.package import InstallError

# Private child-process handoff; never read UV_PYTHON or generic PYTHON* settings.
KEY = "HERMES_PM_SIGNED_PYTHON"


def validate(path: Path, version: str) -> Path:
    if sys.platform != "win32":
        raise InstallError("python", "signed external Python is supported only on Windows")
    import re
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise InstallError("python", f"invalid requested version: {version}")
    path = Path(path).resolve(strict=True)
    if path.name.lower() != "python.exe":
        raise InstallError("python", "signed external Python must be python.exe")
    files = [path, path.parent / f"python{version.split('.')[0]}{version.split('.')[1]}.dll",
             path.parent / "DLLs" / "_ssl.pyd", path.parent / "DLLs" / "_hashlib.pyd",
             path.parent / "DLLs" / "libssl-3.dll", path.parent / "DLLs" / "libcrypto-3.dll"]
    script = (
        "$ErrorActionPreference='Stop'; $names=ConvertFrom-Json $env:HERMES_PM_SIGNATURE_FILES; "
        "$names | ForEach-Object { "
        "$f=Get-Item -LiteralPath $_ -ErrorAction Stop; "
        "$s=Get-AuthenticodeSignature -LiteralPath $f.FullName; "
        "if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'O=Python Software Foundation(,|$)') "
        "{ throw ('invalid Python Software Foundation signature: ' + $f.FullName) } "
        "}"
    )
    env = dict(os.environ, HERMES_PM_SIGNATURE_FILES=json.dumps([str(f) for f in files]))
    try:
        signature = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                   env=env, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError("python", f"signature verification failed: {exc}") from exc
    if signature.returncode:
        raise InstallError("python", f"signature verification failed: {signature.stderr.strip()}")
    try:
        probe = subprocess.run([str(path), "-I", "-c",
                                "import ssl,sys; print('.'.join(map(str,sys.version_info[:3])))"],
                               capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError("python", f"version/ssl probe failed: {exc}") from exc
    if probe.returncode or probe.stdout.strip() != version:
        raise InstallError("python", f"requested version {version}, interpreter reported {probe.stdout.strip()}: {probe.stderr.strip()}")
    return path


def _record_path() -> Path:
    from pm.environments import install_state_dir
    from pm.paths import repo_root

    return install_state_dir(repo_root()) / "signed-python.json"


def record(path: Path) -> None:
    """Publish only after a complete PM install has succeeded."""
    from pm.lock import _write

    _write(_record_path(), {"python": str(path.resolve())})


def reset() -> None:
    _record_path().unlink(missing_ok=True)


def selected() -> Path | None:
    value = os.environ.get(KEY)
    if not value:
        path = _record_path()
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))["python"]
            except (ValueError, KeyError, TypeError, OSError) as exc:
                raise InstallError("python", f"invalid signed Python selection: {path}") from exc
    if not value:
        return None
    from pm.install import _lockfile

    return validate(Path(value), _lockfile().version("python").split("+")[0])
