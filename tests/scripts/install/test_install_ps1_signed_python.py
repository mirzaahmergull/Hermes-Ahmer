"""Windows installer external interpreter opt-in is authenticated before use."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.platforms("windows")
INSTALLER = Path(__file__).resolve().parents[3] / "scripts" / "install.ps1"


def test_bootstrap_accepts_explicit_signed_python_without_uv(tmp_path):
    python = Path(os.environ.get("HERMES_TEST_SIGNED_PYTHON", __import__("sys")._base_executable))
    if not python.is_file():
        pytest.skip("official Python fixture unavailable")
    install = tmp_path / "source"
    (install / "pm").mkdir(parents=True)
    (install / "pm" / "lock.json").write_text(json.dumps({"packages": {"python": {"version": "3.14.7+fixture"}}}))
    wrapper = tmp_path / "probe.ps1"
    wrapper.write_text("param($Installer,$InstallDir,$Py)\n"
                       ". $Installer -InstallDir $InstallDir -SignedPython $Py\n"
                       "function Get-Uv { throw 'uv must not run' }\n"
                       "Get-BootstrapPython\n"
                       "& $env:HERMES_PM_SIGNED_PYTHON -I -c \"import ssl; print('handoff-ok')\"\n", encoding="utf-8-sig")
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(wrapper), "-Installer", str(INSTALLER), "-InstallDir", str(install), "-Py", str(python)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(python).lower() in result.stdout.lower()
    assert "handoff-ok" in result.stdout
    (install / "pm" / "lock.json").write_text(json.dumps({"packages": {"python": {"version": "3.14.8+fixture"}}}))
    mismatch = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                               "-File", str(wrapper), "-Installer", str(INSTALLER), "-InstallDir", str(install), "-Py", str(python)],
                              capture_output=True, text=True, timeout=60)
    assert mismatch.returncode != 0
    assert "version" in (mismatch.stdout + mismatch.stderr).lower()
