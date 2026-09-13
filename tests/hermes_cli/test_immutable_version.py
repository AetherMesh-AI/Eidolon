"""Small offline executable contracts; run directly with Python."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ImmutableVersion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_SYSTEM': os.devnull,
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CEILING_DIRECTORIES': str(self.root.parent)}
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('commit', '--allow-empty', '-m', 'anchor')
        self.git('tag', 'alpha-v0.1.0')
        spec = importlib.util.spec_from_file_location('version', ROOT / 'hermes_cli/eidolon_version.py')
        self.v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.v)
        self.v.ANCHOR_COMMIT = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, env=self.env, stderr=subprocess.DEVNULL, text=True).strip()

    def test_tags_cannot_renumber(self):
        self.git('commit', '--allow-empty', '-m', 'advance')
        before = self.v.resolve_identity(self.root, env={})
        self.git('tag', 'alpha-v9.9.9')
        self.git('tag', '-d', 'alpha-v0.1.0')
        after = self.v.resolve_identity(self.root, env={})
        self.assertEqual(before['version'], '0.1.1')
        self.assertEqual(after['version'], before['version'])
        self.assertIsNotNone(self.v.validate_identity(after))

    def test_merge_once_and_runtime(self):
        self.git('checkout', '-b', 'side')
        for i in range(3): self.git('commit', '--allow-empty', '-m', str(i))
        self.assertEqual(self.v.resolve_identity(self.root, env={})['versionSource'], 'fallback')
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', 'side', '-m', 'merge')
        result = self.v.write_identity(self.root, require_verified=True, env={})
        self.assertEqual(result['version'], '0.1.1')
        self.assertEqual(self.v.runtime_identity(self.root)['version'], result['version'])
        self.git('checkout', '--detach')
        self.assertEqual(self.v.resolve_identity(self.root, env={})['version'], '0.1.1')

    def test_shallow_cannot_reuse_stamp(self):
        self.v.write_identity(self.root, require_verified=True, env={})
        (self.root / '.git/shallow').write_text(self.git('rev-parse', 'HEAD') + '\n')
        with self.assertRaises(ValueError): self.v.write_identity(self.root, require_verified=True, env={})

    def test_actual_desktop_generator_and_runtime_consumer(self):
        import json
        import sys
        source = (ROOT / 'hermes_cli/eidolon_version.py').read_text()
        (self.root / 'hermes_cli').mkdir()
        (self.root / 'hermes_cli/eidolon_version.py').write_text(
            source.replace('437db7394d78a178966fb2ae42792f2978133a9d', self.v.ANCHOR_COMMIT))
        self.git('add', 'hermes_cli')
        self.git('commit', '-m', 'generator')
        generator = (ROOT / 'apps/desktop/scripts/write-build-stamp.mjs').as_uri()
        consumer = (ROOT / 'apps/desktop/electron/install-stamp.ts').as_uri()
        script = f'''import {{writeBuildStamp}} from {json.dumps(generator)};
import {{readInstallStampFromPaths, formatInstallVersion}} from {json.dumps(consumer)};
const stamp = writeBuildStamp({{repoRoot: process.argv[1]}});
const runtime = readInstallStampFromPaths([process.argv[1] + '/apps/desktop/build/install-stamp.json']);
if (runtime.version !== stamp.version || formatInstallVersion(runtime).includes('unverified')) throw Error('consumer mismatch');
console.log(JSON.stringify(runtime));'''
        result = subprocess.check_output(['node', '--experimental-strip-types', '--input-type=module',
            '-e', script, str(self.root)], env={**self.env, 'HERMES_PYTHON': sys.executable}, text=True)
        self.assertEqual(json.loads(result)['version'], '0.1.1')

    def test_unknown_anchor(self):
        self.v.ANCHOR_COMMIT = 'a' * 40
        self.assertEqual(self.v.resolve_identity(self.root, env={})['versionSource'], 'fallback')

if __name__ == '__main__': unittest.main()
