"""Build and promote independent Windows releases of Ahmer's personal fork."""
from __future__ import annotations
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT = Path(r'C:\Hermes-Ahmer')
SOURCE = Path(r'C:\dev\Hermes-Ahmer')
BUILDS = Path(r'C:\dev\Hermes-Ahmer-builds')
HOME = Path(os.environ['LOCALAPPDATA']) / 'hermes'
BOOTSTRAP = ROOT / 'controller-runtime/python.exe'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def git(*args, cwd=SOURCE):
    return subprocess.check_output(['git', '-C', str(cwd), *args], text=True).strip()


def isolated(home):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('HERMES_', 'PYTHON'))
           and not any(x in k.upper() for x in ('API_KEY', 'TOKEN', 'SECRET'))}
    env.update(HERMES_HOME=str(home), UV_CACHE_DIR=str(BUILDS / 'cache/uv'),
               PYTHONIOENCODING='utf-8')
    return env


def release_env(release, home=HOME):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('HERMES_', 'PYTHON'))}
    env.update(HERMES_HOME=str(home), PYTHONIOENCODING='utf-8')
    env.update(HERMES_RUNTIME_DIR=str(release / 'tools'),
               HERMES_INSTALL_ROOT=str(release / 'hermes-agent'))
    return env


def cli(release, *args, home=HOME, capture=False):
    return run([release / 'bin/hermes.exe', *args], env=release_env(release, home),
               capture_output=capture, text=True, encoding='utf-8', timeout=180)


def status():
    for name in ('active', 'candidate', 'previous'):
        path = ROOT / f'{name}.json'
        print(f'{name}: {read(path) if path.exists() else "none"}')


def build(ref):
    if git('status', '--porcelain'):
        raise RuntimeError('Commit or park development changes before building')
    sha = git('rev-parse', '--verify', f'{ref}^{{commit}}')
    name = f'{dt.datetime.now(dt.UTC):%Y%m%d-%H%M%S}-{sha[:12]}'
    job = BUILDS / 'jobs' / name
    source = job / 'source'
    release = ROOT / 'releases' / name
    if release.exists() or job.exists():
        raise RuntimeError('Build paths already exist')
    job.mkdir(parents=True)
    release.mkdir(parents=True)
    run(['git', 'clone', '--local', '--no-hardlinks', SOURCE, source])
    run(['git', '-C', source, 'checkout', '--detach', sha])
    env = isolated(job / 'home')
    env['HERMES_RUNTIME_DIR'] = str(BUILDS / 'cache/tools')
    # Build from the independent committed source, never from the development tree.
    command = [BOOTSTRAP, '-B', source / 'scripts/bundles/stage.py',
               '--out', release, '--ref', sha, '--cache', BUILDS / 'cache/uv',
               '--tools', BUILDS / 'cache/tools']
    for extra in read(source / 'scripts/ahmer/features.json')['extras']:
        command += ['--extra', extra]
    with (job / 'build.log').open('w', encoding='utf-8') as log:
        run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
    desktop_env = dict(env, HERMES_RUNTIME_DIR=str(BUILDS / 'cache/desktop/tools'))
    with (job / 'desktop.log').open('w', encoding='utf-8') as log:
        run([BOOTSTRAP, '-B', source / 'scripts/bundles/desktop.py', '--commit', sha,
             '--variant', 'light', '--work', job / 'desktop', '--cache',
             BUILDS / 'cache/desktop', '--', '--dir'], cwd=source, env=desktop_env,
            stdout=log, stderr=subprocess.STDOUT)
    shutil.copytree(source / 'apps/desktop/release/win-unpacked', release / 'desktop')
    stamp = {'schemaVersion': 2, 'commit': sha, 'branch': 'main',
             'source': 'commit-build', 'updateMechanism': 'external',
             'payload': 'runtime', 'dirty': False, 'baseVersion': '0.21.5',
             'displayVersion': f'Hermes-Ahmer {sha[:12]}', 'builtAt': name}
    write(release / 'hermes-agent/install-stamp.json', stamp)
    shutil.copytree(source / 'scripts/ahmer', release / 'control')
    write(release / 'ahmer-release.json', {'commit': sha, 'id': name,
          'path': str(release), 'source': str(SOURCE), 'verified': False})
    verify(release, job / 'verify-home')
    receipt = read(release / 'ahmer-release.json')
    receipt['verified'] = True
    write(release / 'ahmer-release.json', receipt)
    write(ROOT / 'candidate.json', receipt)
    print(f'Verified candidate: {name}')


def verify(release, home):
    metadata = read(release / 'ahmer-release.json')
    manifest = read(release / 'manifest.json')
    if manifest.get('ref') != metadata['commit']:
        raise RuntimeError('Package revision differs from release receipt')
    for item in ('hermes-agent/Hermes-Ahmer.md', 'bin/hermes.exe',
                 'desktop/Hermes.exe',
                 'hermes-agent/hermes_cli/tui_dist/dist/entry.js',
                 'hermes-agent/hermes_cli/web_dist/index.html'):
        if not (release / item).is_file():
            raise RuntimeError(f'Missing release product: {item}')
    version = cli(release, '--version', home=home, capture=True)
    print(version.stdout)
    for args in (('gateway', '--help'), ('skills', 'list'), ('update', '--check')):
        result = cli(release, *args, home=home, capture=True)
        if args == ('update', '--check') and 'active:' not in result.stdout:
            raise RuntimeError('Production update is not routed to local release controller')
    python = release / manifest['runtime']['storePython']
    site = release / manifest['runtime']['sitePackages']
    code = ("import sys, pathlib; sys.path.insert(0,sys.argv[1]); "
            "import site;site.addsitedir(sys.argv[2]); import hermes_cli.main,slack_sdk,sqlite3; "
            "assert pathlib.Path(hermes_cli.main.__file__).is_relative_to(pathlib.Path(sys.argv[3])); "
            "assert not any('C:\\\\dev\\\\Hermes-Ahmer' == p for p in sys.path); print('Release import paths verified')")
    run([python, '-I', '-c', code, release / 'hermes-agent', site, release],
        env=release_env(release, home))


def user_inventory():
    hashes = {}
    for name in ('.env', 'config.yaml', 'auth.json', 'SOUL.md', 'skills', 'memories',
                 'plugins', 'pairing', 'cron/jobs.json'):
        root = HOME / name
        paths = [root] if root.is_file() else sorted(root.rglob('*')) if root.is_dir() else []
        for path in paths:
            if path.is_file() and '__pycache__' not in path.parts:
                hashes[str(path.relative_to(HOME))] = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    return hashes


def backup():
    directory = ROOT / 'backups' / f'{dt.datetime.now(dt.UTC):%Y%m%d-%H%M%S}'
    directory.mkdir(parents=True)
    # Protect copies of credentials before writing them; existing installation,
    # dependency stores and caches stay intact at their original paths.
    user = os.environ['USERNAME']
    run(['icacls', directory, '/inheritance:r', '/grant:r', f'{user}:(OI)(CI)F',
         'SYSTEM:(OI)(CI)F'], stdout=subprocess.DEVNULL)
    skip = {'hermes-agent', 'tools', 'installs', 'cache', 'audio_cache', 'image_cache'}
    shutil.copytree(HOME, directory / 'home', ignore=lambda p, names: skip.intersection(names) if Path(p) == HOME else [])
    desktop_home = Path(os.environ['APPDATA']) / 'Hermes'
    if desktop_home.exists():
        shutil.copytree(desktop_home, directory / 'desktop-home')
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Hermes.lnk'
    if shortcut.exists():
        shutil.copyfile(shortcut, directory / 'Hermes.lnk')
    run(['schtasks', '/Query', '/TN', 'Hermes_Gateway', '/XML'],
        stdout=(directory / 'gateway-task.xml').open('w', encoding='utf-8'))
    write(directory / 'inventory.json', user_inventory())
    return directory


def original_cli(*args):
    command = ROOT / 'original/hermes.cmd'
    env = dict(os.environ, HERMES_HOME=str(HOME), HERMES_RUNTIME_DIR=str(HOME / 'tools'))
    env.pop('HERMES_INSTALL_ROOT', None)
    return run([command, *args], env=env, text=True, encoding='utf-8', timeout=180)


def database_check():
    for name in ('state.db', 'kanban.db', 'projects.db', 'verification_evidence.db', 'shared-state.db'):
        path = HOME / name
        if path.exists():
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
                result = db.execute('pragma quick_check').fetchone()[0]
                if result != 'ok':
                    raise RuntimeError(f'{name}: {result}')
                print(f'{name}: ok')


def refresh_gateway_launcher(release):
    manifest = read(release / 'manifest.json')
    code = ("import sys;sys.path.insert(0,sys.argv[1]);import hermes_bootstrap;"
            "from hermes_cli.gateway_windows import _write_task_script;"
            "print(_write_task_script())")
    run([release / manifest['runtime']['storePython'], '-I', '-c', code,
         release / 'hermes-agent'], env=release_env(release))


def desktop_shortcut():
    # Keep the existing application identity and Roaming profile.
    script = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:APPDATA+'\\Microsoft\\Windows\\Start Menu\\Programs\\Hermes.lnk');$s.TargetPath='C:\\Windows\\System32\\wscript.exe';$s.Arguments='\"C:\\Hermes-Ahmer\\bin\\desktop.vbs\"';$s.WorkingDirectory='C:\\Hermes-Ahmer';$s.Save()"
    run(['powershell.exe', '-NoProfile', '-Command', script])


def stop_desktop():
    roots = [str(ROOT / 'releases'), str(HOME / 'hermes-agent/apps/desktop/release')]
    env = dict(os.environ, HERMES_AHMER_DESKTOP_ROOTS=json.dumps(roots))
    script = "$roots=ConvertFrom-Json $env:HERMES_AHMER_DESKTOP_ROOTS;$ids=@(Get-CimInstance Win32_Process -Filter \"Name='Hermes.exe'\" | Where-Object {$p=$_.ExecutablePath; $p -and @($roots | Where-Object {$p.StartsWith($_+'\\',[StringComparison]::OrdinalIgnoreCase)}).Count} | ForEach-Object {$_.ProcessId});foreach($id in $ids){$p=Get-Process -Id $id -ErrorAction SilentlyContinue;if($p){[void]$p.CloseMainWindow()}};if($ids.Count){Start-Sleep -Seconds 4;foreach($id in $ids){Stop-Process -Id $id -ErrorAction SilentlyContinue};'running'}"
    result = run(['powershell.exe', '-NoProfile', '-Command', script], env=env,
                 capture_output=True, text=True, timeout=30)
    return 'running' in result.stdout


def launch_desktop():
    run(['wscript.exe', '//B', '//Nologo', ROOT / 'bin/desktop.vbs'])


def deploy(rollback=False):
    selected = ROOT / ('previous.json' if rollback else 'candidate.json')
    receipt = read(selected)
    if receipt.get('kind') == 'original':
        current = read(ROOT / 'active.json')
        desktop_was_running = stop_desktop()
        cli(Path(current['path']), 'serve', '--stop')
        cli(Path(current['path']), 'gateway', 'stop')
        saved = backup()
        # Restore the launchers and home snapshot together; preserve current data
        # in the fresh backup. Copy rather than deleting any directory.
        if receipt.get('backup'):
            shutil.copytree(Path(receipt['backup']) / 'home', HOME, dirs_exist_ok=True)
        shutil.copyfile(ROOT / 'original/hermes.cmd', HOME / 'bin/hermes.cmd')
        shutil.copyfile(ROOT / 'original/hermes-acp.cmd', HOME / 'bin/hermes-acp.cmd')
        write(ROOT / 'active.json', receipt)
        write(ROOT / 'previous.json', {**current, 'backup': str(saved)})
        original_cli('gateway', 'start')
        if receipt.get('backup') and (Path(receipt['backup']) / 'Hermes.lnk').exists():
            shutil.copyfile(Path(receipt['backup']) / 'Hermes.lnk',
                            Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Hermes.lnk')
        print('Original installation restored; newer data snapshot retained at ' + str(saved))
        return
    release = Path(receipt['path']).resolve()
    if not release.is_relative_to((ROOT / 'releases').resolve()) or not receipt['verified']:
        raise RuntimeError('Refusing unverified or external release')
    current = read(ROOT / 'active.json') if (ROOT / 'active.json').exists() else None
    if current and current['path'] == str(release):
        print('Selected release is already active')
        return
    # Never run concurrent gateways against the same user home.
    desktop_was_running = stop_desktop()
    old = Path(current['path']) if current and current.get('kind') != 'original' else None
    if current and current.get('kind') == 'original':
        original_cli('serve', '--stop')
        original_cli('gateway', 'stop')
    elif old:
        cli(old, 'serve', '--stop')
        cli(old, 'gateway', 'stop')
    else:
        run([HOME / 'bin/hermes.cmd', 'serve', '--stop'])
        run([HOME / 'bin/hermes.cmd', 'gateway', 'stop'])
        original = ROOT / 'original'
        original.mkdir(exist_ok=True)
        for name in ('hermes.cmd', 'hermes-acp.cmd'):
            shutil.copyfile(HOME / 'bin' / name, original / name)
    saved = backup()
    if rollback and receipt.get('backup'):
        shutil.copytree(Path(receipt['backup']) / 'home', HOME, dirs_exist_ok=True)
    before = user_inventory()
    database_check()
    if current:
        write(ROOT / 'previous.json', {**current, 'backup': str(saved)})
    else:
        write(ROOT / 'previous.json', {'kind': 'original', 'id': 'original-installation',
              'path': str(HOME / 'hermes-agent'), 'verified': True, 'backup': str(saved)})
    write(ROOT / 'active.json', {**receipt, 'backup': str(saved)})
    try:
        for name in ('hermes', 'hermes-acp'):
            target = HOME / 'bin' / f'{name}.cmd'
            prefix = '' if name == 'hermes' else '--run-module acp_adapter.entry '
            target.write_text('@echo off\ncall "C:\\Hermes-Ahmer\\bin\\hermes.cmd" ' + prefix + '%*\n', encoding='utf-8')
        (HOME / 'bin/ahmer-release.cmd').write_text(
            '@echo off\ncall "C:\\Hermes-Ahmer\\bin\\ahmer-release.cmd" %*\n', encoding='utf-8')
        refresh_gateway_launcher(release)
        cli(release, 'gateway', 'start')
        time.sleep(15)
        result = cli(release, 'gateway', 'status', capture=True)
        if 'Gateway process running' not in result.stdout:
            raise RuntimeError('Gateway failed to remain alive: ' + result.stdout)
        print(result.stdout)
        desktop_shortcut()
        after = user_inventory()
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        write(ROOT / 'deployment.json', {'release': receipt['id'], 'backup': str(saved),
              'changedUserFiles': changed, 'verifiedAt': dt.datetime.now(dt.UTC).isoformat()})
        if changed:
            print('User files changed during startup; review deployment.json: ' + ', '.join(changed))
        database_check()
        if desktop_was_running:
            launch_desktop()
    except Exception:
        with contextlib.suppress(Exception):
            cli(release, 'gateway', 'stop')
        shutil.copytree(saved / 'home', HOME, dirs_exist_ok=True)
        shortcut = saved / 'Hermes.lnk'
        if shortcut.exists():
            shutil.copyfile(shortcut, Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Hermes.lnk')
        if current:
            write(ROOT / 'active.json', current)
            if current.get('kind') == 'original': original_cli('gateway', 'start')
            else: cli(Path(current['path']), 'gateway', 'start')
        else:
            for name in ('hermes.cmd', 'hermes-acp.cmd'):
                shutil.copyfile(ROOT / 'original' / name, HOME / 'bin' / name)
            write(ROOT / 'active.json', read(ROOT / 'previous.json'))
            original_cli('gateway', 'start')
        raise
    print(f'Production deployed: {receipt["id"]}; data remains at {HOME}')


def install_controller():
    bindir = ROOT / 'bin'
    bindir.mkdir(parents=True, exist_ok=True)
    if not BOOTSTRAP.exists():
        original_python = HOME / 'tools/python-3.14.7+20260901-win32-x64'
        shutil.copytree(original_python, BOOTSTRAP.parent)
    shutil.copyfile(__file__, bindir / 'release.py')
    (bindir / 'ahmer-release.cmd').write_text(
        f'@echo off\n"{BOOTSTRAP}" -I "{bindir / "release.py"}" %*\n', encoding='utf-8')
    (bindir / 'run.ps1').write_text('''param([Parameter(ValueFromRemainingArguments=$true)][string[]]$HermesArgs)
$ErrorActionPreference = 'Stop'
$release = (Get-Content -LiteralPath 'C:\\Hermes-Ahmer\\active.json' -Raw | ConvertFrom-Json).path
$env:HERMES_HOME = "$env:LOCALAPPDATA\\hermes"
$env:HERMES_INSTALL_ROOT = Join-Path $release 'hermes-agent'
$env:HERMES_RUNTIME_DIR = Join-Path $release 'tools'
Remove-Item Env:PYTHONPATH,Env:PYTHONHOME,Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
& (Join-Path $release 'bin\\hermes.exe') @HermesArgs
exit $LASTEXITCODE
''', encoding='utf-8')
    (bindir / 'run.py').write_text('''import json, os, subprocess, sys
from pathlib import Path
selection = json.loads(Path(r'C:\\Hermes-Ahmer\\active.json').read_text())
root = Path(selection['path'])
args = sys.argv[1:]
if selection.get('kind') == 'original':
    env = dict(os.environ, HERMES_HOME=str(Path(os.environ['LOCALAPPDATA']) / 'hermes'),
               HERMES_RUNTIME_DIR=str(Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'tools'))
    env.pop('HERMES_INSTALL_ROOT', None)
    sys.exit(subprocess.call([r'C:\\Hermes-Ahmer\\original\\hermes.cmd', *args], env=env))
name = 'hermes.exe'
if args[:2] == ['--run-module', 'acp_adapter.entry']:
    name, args = 'hermes-acp.exe', args[2:]
env = dict(os.environ, HERMES_HOME=str(Path(os.environ['LOCALAPPDATA']) / 'hermes'),
           HERMES_INSTALL_ROOT=str(root / 'hermes-agent'), HERMES_RUNTIME_DIR=str(root / 'tools'))
for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
    env.pop(key, None)
sys.exit(subprocess.call([str(root / 'bin' / name), *args], env=env))
''', encoding='utf-8')
    (bindir / 'hermes.cmd').write_text(
        f'@echo off\n"{BOOTSTRAP}" -I "{bindir / "run.py"}" %*\n', encoding='utf-8')
    (bindir / 'desktop.py').write_text('''import json, os, subprocess
from pathlib import Path
root = Path(json.loads(Path(r'C:\\Hermes-Ahmer\\active.json').read_text())['path'])
manifest = json.loads((root / 'manifest.json').read_text())
env = dict(os.environ, HERMES_HOME=str(Path(os.environ['LOCALAPPDATA']) / 'hermes'),
           HERMES_RUNTIME_DIR=str(root / 'tools'),
           HERMES_DESKTOP_HERMES_ROOT=str(root / 'hermes-agent'),
           HERMES_DESKTOP_PYTHON=str(root / manifest['runtime']['storePython']))
for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
    env.pop(key, None)
subprocess.Popen([str(root / 'desktop/Hermes.exe')], env=env, cwd=root)
''', encoding='utf-8')
    (bindir / 'desktop.vbs').write_text(
        f'CreateObject("WScript.Shell").Run """{BOOTSTRAP}"" -I ""{bindir / "desktop.py"}""", 0, False\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'deploy', 'rollback', 'status', 'controller'])
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    if args.action == 'status':
        status()
        return
    import msvcrt
    with (ROOT / 'release.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        if args.action == 'controller': install_controller()
        elif args.action == 'build': build(args.ref)
        elif args.action == 'status': status()
        else: deploy(args.action == 'rollback')


if __name__ == '__main__':
    main()
