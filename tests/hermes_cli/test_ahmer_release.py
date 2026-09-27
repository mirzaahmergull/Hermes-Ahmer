"""Personal releases must never fall through to official update machinery."""
from argparse import Namespace
from hermes_cli.ahmer_release import handle_update


def test_development_fork_refuses_inplace_update(tmp_path, capsys):
    (tmp_path / 'Hermes-Ahmer.md').write_text('fork')
    assert handle_update(tmp_path, Namespace(gateway=False, check=False, plan=False))
    assert 'Official self-update is disabled' in capsys.readouterr().out


def test_nonfork_retains_upstream_update(tmp_path):
    assert not handle_update(tmp_path, Namespace())
