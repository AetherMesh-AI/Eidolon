"""Version transition reporting after ``hermes update``.

Ported from PrimeIntellect-ai/prime-agent#630: a successful self-update
reports both versions (``v0.19.4 → v0.20.0``) when the pyproject version
changed, and degrades gracefully when either side is unknown.
"""

from pathlib import Path

import pytest

from hermes_cli import update_cmd


def _write_pyproject(root: Path, version: str) -> None:
    # Package declarations stay at the floor; only generated identity is current.
    import json
    from hermes_cli.eidolon_version import fallback
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.1"\n')
    (root / 'hermes_cli').mkdir(exist_ok=True)
    identity = fallback('a' * 40, False)
    identity.update(version=version, baseTag=f'alpha-v{version}', baseCommit='a' * 40,
                    distance=0, versionSource='stamp')
    (root / 'hermes_cli/_build_identity.json').write_text(json.dumps(identity))


@pytest.fixture()
def fake_root(tmp_path, monkeypatch):
    class _FakeMain:
        PROJECT_ROOT = tmp_path

    monkeypatch.setattr(update_cmd, "_m", lambda: _FakeMain)
    return tmp_path


class TestReadProjectVersion:
    def test_refreshes_after_build_in_same_process(self, fake_root):
        _write_pyproject(fake_root, '0.1.12')
        assert update_cmd._read_project_version() == '0.1.12'
        _write_pyproject(fake_root, '0.1.13')
        assert update_cmd._update_complete_message('0.1.12') == '✓ Update complete! (v0.1.12 → v0.1.13)'

    def test_static_floor_is_not_a_development_identity(self, fake_root):
        (fake_root / 'pyproject.toml').write_text('[project]\nversion = "9.9.9"\n')
        assert update_cmd._read_project_version() is None

    def test_reads_version(self, fake_root):
        _write_pyproject(fake_root, "0.20.0")
        assert update_cmd._read_project_version() == "0.20.0"

    def test_missing_file_returns_none(self, fake_root):
        assert update_cmd._read_project_version() is None

    def test_malformed_toml_returns_none(self, fake_root):
        (fake_root / "pyproject.toml").write_text("not [ toml", encoding="utf-8")
        assert update_cmd._read_project_version() is None


class TestUpdateCompleteMessage:
    def test_reports_transition_when_version_changed(self, fake_root):
        _write_pyproject(fake_root, "0.20.0")
        assert (
            update_cmd._update_complete_message("0.19.4")
            == "✓ Update complete! (v0.19.4 → v0.20.0)"
        )

    def test_same_version_reports_single_version(self, fake_root):
        _write_pyproject(fake_root, "0.20.0")
        assert (
            update_cmd._update_complete_message("0.20.0")
            == "✓ Update complete! (v0.20.0)"
        )

    def test_unknown_pre_version_still_shows_current(self, fake_root):
        _write_pyproject(fake_root, "0.20.0")
        assert (
            update_cmd._update_complete_message(None)
            == "✓ Update complete! (v0.20.0)"
        )

    def test_unknown_post_version_falls_back_to_plain(self, fake_root):
        assert update_cmd._update_complete_message("0.19.4") == "✓ Update complete!"
