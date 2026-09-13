"""Offline upstream contracts. No live updater, transport or application."""
import ast
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]

def function(file, name, **scope):
    tree = ast.parse((ROOT / file).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), file, 'exec'), scope)
    return scope[name]

class UpstreamAlignment(unittest.TestCase):
    def test_network_git_has_bounded_timeout(self):
        run = Mock(side_effect=subprocess.TimeoutExpired(['git', 'fetch'], 300))
        proxy = types.SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired,
            CompletedProcess=subprocess.CompletedProcess, CalledProcessError=subprocess.CalledProcessError)
        call = function('hermes_cli/update_cmd.py', '_git_run', subprocess=proxy,
            NETWORK_GIT_TIMEOUT_SECONDS=300, _no_prompt_git_kwargs=lambda: {}, _m=lambda: None)
        result = call(['git'], ['fetch', 'origin', 'main'], cwd='/fixture', network=True)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(run.call_args.kwargs['timeout'], 300)
        with self.assertRaises(subprocess.CalledProcessError):
            call(['git'], ['fetch'], cwd='/fixture', network=True, check=True)

    def test_apply_fetch_completes_history_before_build(self):
        tree = ast.parse((ROOT / 'hermes_cli/update_cmd.py').read_text())
        body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_cmd_update_impl')
        statements: list[ast.stmt] = [n for n in ast.walk(body) if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id in ('history_args', 'fetch_result') for t in n.targets)]
        code = compile(ast.Module(body=statements, type_ignores=[]), 'apply-fetch', 'exec')
        for shallow in (True, False):
            run = Mock()
            exec(code, {'_is_shallow_checkout': lambda _: shallow, '_git_run': run,
                'git_cmd': ['git'], 'branch': 'main'})
            self.assertEqual(run.call_args.args[1], ['fetch'] + (['--unshallow'] if shallow else []) + ['origin', 'main'])
            self.assertTrue(run.call_args.kwargs['network'])

    def test_official_upstream_add_is_not_disabled(self):
        git = Mock(return_value=True)
        call = function('hermes_cli/update_cmd_git.py', '_add_upstream_remote',
            Path=Path, _git_ok=git, OFFICIAL_REPO_URL='https://github.com/AetherMesh-AI/Eidolon.git')
        self.assertTrue(call(['git'], Path('/fixture')))
        self.assertEqual(git.call_args.args[1], ['remote', 'add', 'upstream', 'https://github.com/AetherMesh-AI/Eidolon.git'])

    def test_linux_symlink_is_not_package_skew(self):
        # Execute only the production gate, with portable readlink emulation on macOS.
        text = (ROOT / 'scripts/desktop-update/posix.sh').read_text()
        gate = text[text.index('linux_gate() {'):text.index('\nmac_swap()')]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = root / 'actual'
            unpacked = actual / 'apps/desktop/release/linux-unpacked'
            unpacked.mkdir(parents=True)
            (root / 'link').symlink_to(actual, target_is_directory=True)
            script = '''readlink() { python3 -c 'import os,sys; print(os.path.realpath(sys.argv[-1]))' "$@"; }
''' + gate + '''
GATE=""; GATE_MSG=""; RELAUNCH_ARGS=(--no-sandbox)
linux_gate
[ "$GATE" != skew ]
'''
            result = subprocess.run(['bash', '-c', script], env={**__import__('os').environ,
                'INSTALL_ROOT': str(root / 'link'), 'RELAUNCH_TARGET': str(unpacked / 'eidolon')}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_windows_real_cwd_setup_precedes_update(self):
        text = (ROOT / 'scripts/desktop-update/windows.ps1').read_text()
        self.assertIn('[Environment]::CurrentDirectory = $resolved', text)
        self.assertLess(text.index('$resolvedInstallRoot = Set-InstallRootCurrentDirectory'), text.index('$pythonExe = Join-Path $InstallRoot'))
        self.assertIn('WORKING-DIRECTORY SELF-TEST: PASS', text)

if __name__ == '__main__': unittest.main()
