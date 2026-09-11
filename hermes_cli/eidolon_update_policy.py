"""Eidolon source identity. Git ancestry, never SHA ordering, defines updates."""
from pathlib import Path
import re
import subprocess

UPDATE_REPO = 'AetherMesh-AI/Eidolon'
UPDATE_BRANCH = 'main'
UPDATE_URL = f'https://github.com/{UPDATE_REPO}.git'


def is_official_source(url: str) -> bool:
    return url.strip().lower() in {
        f'https://github.com/{UPDATE_REPO}'.lower(),
        UPDATE_URL.lower(),
        f'git@github.com:{UPDATE_REPO}.git'.lower(),
        f'ssh://git@github.com/{UPDATE_REPO}.git'.lower(),
    }


def relation(root: Path, local: str = 'HEAD', target: str = 'origin/main') -> str:
    """Read-only comparison. Unknown/missing objects fail rather than imply current."""
    def git(*args):
        return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=15)
    left, right = (git('rev-parse', '--verify', f'{ref}^{{commit}}') for ref in (local, target))
    if left.returncode or right.returncode:
        raise ValueError('Cannot resolve update commits')
    if left.stdout == right.stdout:
        return 'current'
    for a, b, label in [(left.stdout.strip(), right.stdout.strip(), 'behind'),
                         (right.stdout.strip(), left.stdout.strip(), 'ahead')]:
        result = git('merge-base', '--is-ancestor', a, b)
        if result.returncode == 0:
            return label
        if result.returncode != 1:
            raise ValueError('Cannot determine update ancestry')
    return 'diverged'


def build_identity(root: Path | None = None) -> dict:
    """Exact source HEAD plus dirty state; non-Git copies report unknown honestly."""
    root = root or Path(__file__).resolve().parents[1]
    result = {'version': '0.1.0', 'channel': 'alpha', 'commit': None, 'dirty': None}
    if not (root / '.git').exists():
        return result
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, stderr=subprocess.DEVNULL, text=True, timeout=3).strip()
        if re.fullmatch(r'[0-9a-f]{40}', sha):
            result['commit'] = sha
            result['dirty'] = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=root, stderr=subprocess.DEVNULL, text=True, timeout=3).strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return result
