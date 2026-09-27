"""An external controller's launcher must survive Windows startup repair."""
from hermes_cli import _launchers, steward


def test_windows_exposure_preserves_external_controller(tmp_path, monkeypatch):
    root = tmp_path / "release" / "hermes-agent"
    root.mkdir(parents=True)
    user_bin = tmp_path / "home" / "bin"
    user_bin.mkdir(parents=True)
    launcher = user_bin / "hermes.cmd"
    launcher.write_text('@echo off\ncall "C:\\Hermes-Ahmer\\bin\\hermes.cmd" %*\n')
    before = launcher.read_bytes()
    monkeypatch.setattr(_launchers, "_is_windows", lambda: True)
    monkeypatch.setattr(steward, "read_install_stamp", lambda _: {"updateMechanism": "external"})

    def forbidden(*args, **kwargs):
        raise AssertionError("External controller commands must not be republished")

    monkeypatch.setattr(_launchers, "_expose_windows_user_bin", forbidden)
    assert _launchers.expose_cli(root) == {"ok": True, "skipped": "externally-owned"}
    assert _launchers.expose_cli(root, create=False) == {"ok": True, "skipped": "externally-owned"}
    assert launcher.read_bytes() == before
