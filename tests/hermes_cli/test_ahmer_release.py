"""Personal releases must never fall through to official update machinery."""
from argparse import Namespace
from hermes_cli.ahmer_release import handle_update


def test_development_fork_refuses_inplace_update(tmp_path, capsys):
    (tmp_path / 'Hermes-Ahmer.md').write_text('fork')
    assert handle_update(tmp_path, Namespace(gateway=False, check=False, plan=False))
    assert 'Official self-update is disabled' in capsys.readouterr().out


def test_nonfork_retains_upstream_update(tmp_path):
    assert not handle_update(tmp_path, Namespace())


def test_production_routes_checks_and_updates_to_local_controller(tmp_path, monkeypatch):
    import hermes_cli.ahmer_release as module
    root = tmp_path / 'hermes-agent'
    root.mkdir()
    (root / 'Hermes-Ahmer.md').touch()
    (tmp_path / 'ahmer-release.json').touch()
    controller = tmp_path / 'controller.cmd'
    controller.touch()
    monkeypatch.setattr(module, 'CONTROLLER', controller)
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda argv, **kwargs:
                        calls.append(argv) or Namespace(returncode=0))
    assert handle_update(root, Namespace(check=True))
    assert handle_update(root, Namespace(check=False))
    assert calls == [[str(controller), 'status'], [str(controller), 'deploy']]


def test_contained_runtime_subcommands_keep_the_release_launcher(tmp_path):
    import json
    from hermes_cli._launchers import installation_command
    root = tmp_path / 'hermes-agent'
    root.mkdir()
    command = tmp_path / 'bin/hermes.exe'
    command.parent.mkdir()
    command.touch()
    (tmp_path / 'manifest.json').write_text(json.dumps({
        'repo': 'hermes-agent', 'runtime': {'commands': {'hermes': 'bin/hermes.exe'}}}))
    assert installation_command(root, ['serve']) == [str(command), 'serve']
