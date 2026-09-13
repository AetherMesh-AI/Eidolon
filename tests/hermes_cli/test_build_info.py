"""Tests for hermes_cli.build_info — baked-in build SHA resolution.

The build SHA is written by the Dockerfile's ``HERMES_GIT_SHA`` build-arg
into ``<project_root>/.hermes_build_sha``.  These tests cover the read-side
helper: missing file, malformed file, truncation, and error tolerance.
"""

from pathlib import Path
from unittest.mock import patch


def test_get_build_sha_returns_none_when_file_absent(tmp_path):
    """Source installs: no file present → None, callers fall back to git."""
    from hermes_cli import build_info

    missing = tmp_path / ".hermes_build_sha"  # never created

    with patch.object(build_info, "_BUILD_SHA_FILE", missing):
        assert build_info.get_build_sha() is None


def test_get_build_sha_respects_short_argument(tmp_path):
    """``short=N`` truncates to N chars; ``short<=0`` returns full SHA."""
    from hermes_cli import build_info

    sha_file = tmp_path / ".hermes_build_sha"
    full_sha = "abcdef1234567890abcdef1234567890abcdef12"
    sha_file.write_text(full_sha + "\n")

    with patch.object(build_info, "_BUILD_SHA_FILE", sha_file):
        assert build_info.get_build_sha(short=12) == "abcdef123456"
        assert build_info.get_build_sha(short=0) == full_sha
        assert build_info.get_build_sha(short=-1) == full_sha


def test_generated_version_cache_refresh_and_spawn_free(tmp_path, monkeypatch):
    import json
    import subprocess
    from hermes_cli import build_info
    from hermes_cli.eidolon_version import fallback
    package = tmp_path / 'hermes_cli'
    package.mkdir()
    monkeypatch.setattr(build_info, '__file__', str(package / 'build_info.py'))
    monkeypatch.setattr(build_info, '_BUILD_SHA_FILE', tmp_path / '.hermes_build_sha')
    monkeypatch.setattr(build_info, '_code_identity_cache', None)
    def forbidden(*a, **kw): raise AssertionError('runtime spawned a process')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    value = fallback('a' * 40, False)
    value.update(version='0.1.12', versionSource='stamp', baseTag='alpha-v0.1.0',
                 baseCommit='b' * 40, distance=12)
    stamp = package / '_build_identity.json'
    stamp.write_text(json.dumps(value))
    first = build_info.get_code_identity()
    assert first['version'] == '0.1.12' and first['sha'] == 'a' * 40
    assert first['version_source'] == 'stamp' and first['channel'] == 'alpha'
    value.update(version='0.1.13', distance=13)
    stamp.write_text(json.dumps(value))
    assert build_info.get_code_identity()['version'] == '0.1.12'
    assert build_info.get_code_identity(refresh=True)['version'] == '0.1.13'
    stamp.unlink()
    assert build_info.get_code_identity(refresh=True)['version_source'] == 'fallback'


