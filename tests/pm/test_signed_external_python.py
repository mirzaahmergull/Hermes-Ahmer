"""Explicit signed Windows interpreter cannot be replaced by ambient uv discovery."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.pm.test_uv_python import installed_uv  # reuse isolated PM store fixture

pytestmark = pytest.mark.platforms("windows")


def _signed_python():
    path = Path(os.environ.get("HERMES_TEST_SIGNED_PYTHON", sys._base_executable))
    if not path.is_file():
        pytest.skip("official signed Python fixture unavailable")
    return path


def test_signed_selection_checks_version_and_dll_signatures(monkeypatch):
    from pm.signed_python import validate
    from pm._uv import _toolchain
    from pm.lock import Lockfile
    from pm import paths

    python = _signed_python()
    assert validate(python, "3.14.7") == python.resolve()
    with pytest.raises(Exception, match="version"):
        validate(python, "3.14.8")
    with pytest.raises(Exception, match="signature|signed"):
        validate(Path(sys.executable), "3.14.7")
    monkeypatch.setenv("UV_PYTHON", "C:/untrusted/python.exe")
    monkeypatch.setenv("HERMES_PM_SIGNED_PYTHON", str(python))
    # A separate internal selection is explicit and checked against PM's requested pin.
    pin = Lockfile(paths.lockfile_path()).version("python").split("+")[0]
    if pin == "3.14.7":
        from pm.signed_python import selected
        assert selected() == python.resolve()
    else:
        with pytest.raises(Exception, match="version"):
            from pm.signed_python import selected
            selected()


def test_signature_probe_ignores_pwsh_module_path(monkeypatch):
    from pm.signed_python import validate

    # PowerShell 7 prepends its incompatible built-in modules. Its child
    # Windows PowerShell must resolve Microsoft.PowerShell.Security itself.
    monkeypatch.setenv("PSModulePath", r"C:\Program Files\PowerShell\7\Modules")
    assert validate(_signed_python(), "3.14.7") == _signed_python().resolve()


def test_venv_stamp_changes_when_switching_to_signed_python(monkeypatch):
    from pm.packages import Venv
    from pm.signed_python import KEY

    monkeypatch.delenv(KEY, raising=False)
    before = Venv().expected_stamp([], plugin_dirs=[])
    monkeypatch.setenv(KEY, str(_signed_python()))
    after = Venv().expected_stamp([], plugin_dirs=[])
    assert before != after


def test_toolchain_uses_signed_python_without_pinned_python(monkeypatch, installed_uv):
    from pm._uv import _toolchain
    from pm.lock import Lockfile
    from pm import paths
    python = _signed_python()
    # The fixture pin is deliberately incompatible: invalid explicit selection must fail closed.
    monkeypatch.setenv("HERMES_PM_SIGNED_PYTHON", str(python))
    with pytest.raises(Exception, match="version"):
        _toolchain(realize=False)


def test_cli_reset_signed_python_does_not_bootstrap_runtime(tmp_path, monkeypatch):
    import pm.paths as paths
    from pm.signed_python import record, selected
    from pm.cli import main
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    record(_signed_python())
    assert main(["reset-signed-python"]) == 0
    monkeypatch.delenv("HERMES_PM_SIGNED_PYTHON", raising=False)
    assert selected() is None


def test_signed_selection_survives_fresh_process_without_handoff(tmp_path, monkeypatch):
    from pm.signed_python import selected, record, reset
    from pm import paths
    python = _signed_python()
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(paths, "lockfile_path", lambda: tmp_path / "lock.json")
    from pm.lock import Lockfile
    from pm.store import current_target
    lock = Lockfile(tmp_path / "lock.json")
    lock.set_pin("python", "3.14.7+fixture", {current_target(): {"url": "https://test.invalid/python", "sha256": "1" * 64}})
    lock.save()
    monkeypatch.delenv("HERMES_PM_SIGNED_PYTHON", raising=False)
    assert selected() is None
    record(python)
    assert selected() == python.resolve()
    code = ("import sys; from pathlib import Path; import pm.paths as p; "
            "p.repo_root=lambda:Path(sys.argv[1]); "
            "p.lockfile_path=lambda:Path(sys.argv[1])/'lock.json'; "
            "from pm.signed_python import selected; print(selected())")
    child = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
                           cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=True)
    assert Path(child.stdout.strip()) == python.resolve()
    reset()
    assert selected() is None


def test_build_cli_accepts_signed_python_as_selected_interpreter(tmp_path, monkeypatch):
    from pm.build_env import main
    import pm
    python = _signed_python()
    monkeypatch.setattr(pm, "build_environment", lambda **kwargs: kwargs["python"])
    result = main(["--source", str(tmp_path), "--out", str(tmp_path / "venv"),
                   "--signed-python", str(python)])
    assert result == 0


def test_build_environment_uses_explicit_signed_python_and_rejects_ambient(monkeypatch, tmp_path, installed_uv):
    from pm.environment import managed_environment
    from pm.lock import Lockfile
    from pm import paths
    python = _signed_python()
    root, uv, facts, target, digest = installed_uv
    lock = Lockfile(paths.lockfile_path())
    lock.set_pin("python", "3.14.7+fixture", {target: {"url": "https://test.invalid/python", "sha256": digest}})
    lock.save()
    monkeypatch.setenv("UV_PYTHON", "C:/untrusted/python.exe")
    monkeypatch.setenv("HERMES_PM_SIGNED_PYTHON", str(python))
    environment = managed_environment(tmp_path / "venv", realize=False)
    assert environment.python == python.resolve()
    assert environment.uv == uv
    assert "UV_PYTHON" not in environment.env
