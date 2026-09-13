"""Import production source callers without Electron or a live updater."""
import os
from pathlib import Path
import subprocess


def test_archive_update_callers(tmp_path):
    root = Path(__file__).resolve().parents[1]
    harness = root / "tests/fixtures/desktop_archive_update.cjs"
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path / "home"),
           "HERMES_HOME": str(tmp_path / "home/.eidolon"),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CEILING_DIRECTORIES": str(tmp_path),
           "TYPESCRIPT_JS": str(root / "node_modules/typescript/lib/typescript.js")}
    Path(env["HERMES_HOME"]).mkdir(parents=True)
    result = subprocess.run(["node", str(harness), str(root), str(tmp_path)], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: archive check" in result.stdout
