"""Manual alpha release: stdlib-only policy, packaging verification and GitHub API.

Inputs arrive ONLY through environment variables. No changelog is checked in.
Publication refuses existing tags/releases, including failed draft attempts.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import shutil

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / 'apps/desktop'
VARIANTS = [('darwin', 'arm64', 'macos', 'pkg'),
            ('linux', 'arm64', 'linux', 'AppImage'), ('linux', 'x64', 'linux', 'AppImage'),
            ('win32', 'arm64', 'windows', 'exe'), ('win32', 'x64', 'windows', 'exe')]


def validate_inputs(tag, body, version):
    if not re.fullmatch(r'alpha-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag):
        raise ValueError('Tag must be alpha-vMAJOR.MINOR.PATCH (no leading zeroes)')
    if tag != 'alpha-v' + version:
        raise ValueError('Tag must match committed desktop version; bump source metadata first')
    if not body.strip() or '\0' in body or len(body.encode('utf-8')) > 60000:
        raise ValueError('Changelog Markdown must be nonblank, NUL-free and <= 60000 UTF-8 bytes')
    return body


def asset_names(tag):
    return [f'{label}_{arch}_{tag}.{ext}' for _, arch, label, ext in VARIANTS]


def file_record(path):
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    return {'name': path.name, 'size': path.stat().st_size, 'digest': 'sha256:' + digest}


def local_assets(root, tag):
    paths = list(root.iterdir())
    if sorted(p.name for p in paths) != sorted(asset_names(tag)):
        raise ValueError('Release directory must contain exactly the five expected assets')
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size == 0 for p in paths):
        raise ValueError('Assets must be nonempty regular files, never symlinks')
    return [file_record(p) for p in sorted(paths)]


def verify_remote_assets(local, remote):
    wanted = sorted(local, key=lambda a: a['name'])
    actual = sorted(({k: a.get(k) for k in ('name', 'size', 'digest')} for a in remote), key=lambda a: a['name'])
    if actual != wanted or any(a.get('state') != 'uploaded' for a in remote):
        raise ValueError('GitHub assets must match exact names, sizes and SHA-256 digests, all uploaded')


class API:
    def __init__(self):
        self.base = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
        self.token = os.environ['GH_TOKEN']

    def request(self, method, path, data=None, file=None, missing=False):
        url = path if path.startswith('https://') else self.base + path
        # Never send the token to arbitrary hosts or follow authenticated redirects.
        if urllib.parse.urlparse(url).hostname not in ('api.github.com', 'uploads.github.com'):
            raise ValueError('Unexpected GitHub API host')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        headers = {'Authorization': 'Bearer ' + self.token,
                   'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                   'User-Agent': 'Eidolon-manual-release'}
        payload = None
        handle = None
        if file:
            handle = file.open('rb')
            payload = handle
            headers.update({'Content-Type': 'application/octet-stream', 'Content-Length': str(file.stat().st_size)})
        elif data is not None:
            payload = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        try:
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            with urllib.request.build_opener(NoRedirect).open(request, timeout=600) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RuntimeError(f'GitHub {method} {path}: HTTP {error.code}; no automatic cleanup/retry') from error
        finally:
            if handle is not None:
                handle.close()


def absent(api, tag):
    if api.request('GET', '/git/ref/tags/' + tag, missing=True) is not None:
        raise ValueError('Tag already exists; never reuse, move or delete it automatically')
    if api.request('GET', '/releases/tags/' + tag, missing=True) is not None:
        raise ValueError('Release/draft already exists; inspect manually before retrying')


def verify_ref(api, tag, sha):
    ref = api.request('GET', '/git/ref/tags/' + tag)
    if ref['object']['sha'] != sha:
        raise ValueError('Tag does not point to the immutable build commit')


def verify_release(release, tag, sha, body, draft):
    expected = dict(tag_name=tag, target_commitish=sha, name='Eidolon ' + tag,
                    body=body, draft=draft, prerelease=True)
    if any(release.get(k) != v for k, v in expected.items()):
        raise ValueError('Release metadata readback differs from requested values')


def publish(api, root, tag, sha, body):
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or sha == '0' * 40:
        raise ValueError('Immutable 40-character source SHA required')
    local = local_assets(root, tag)
    absent(api, tag)
    # Atomic create, never an update: catches collisions after preflight.
    api.request('POST', '/git/refs', {'ref': 'refs/tags/' + tag, 'sha': sha})
    verify_ref(api, tag, sha)
    release = api.request('POST', '/releases', dict(tag_name=tag, target_commitish=sha,
        name='Eidolon ' + tag, body=body, draft=True, prerelease=True,
        generate_release_notes=False, make_latest='false'))
    endpoint = '/releases/' + str(release['id'])
    verify_release(api.request('GET', endpoint), tag, sha, body, True)
    upload = release['upload_url'].split('{')[0]
    for asset in local:
        api.request('POST', upload + '?' + urllib.parse.urlencode({'name': asset['name']}), file=root / asset['name'])
    verify_remote_assets(local, api.request('GET', endpoint + '/assets?per_page=100'))
    verify_ref(api, tag, sha)
    verify_release(api.request('GET', endpoint), tag, sha, body, True)
    api.request('PATCH', endpoint, {'draft': False, 'prerelease': True, 'make_latest': 'false'})
    verify_release(api.request('GET', endpoint), tag, sha, body, False)
    verify_remote_assets(local, api.request('GET', endpoint + '/assets?per_page=100'))
    verify_ref(api, tag, sha)
    print('Published and read back ' + tag + ' with exactly five verified assets')


def binary_target(data):
    if data[:4] == b'\x7fELF' and data[4:6] == b'\x02\x01':
        return 'linux', {62: 'x64', 183: 'arm64'}[struct.unpack_from('<H', data, 18)[0]]
    if data[:4] == b'\xcf\xfa\xed\xfe':
        return 'darwin', {0x1000007: 'x64', 0x100000c: 'arm64'}[struct.unpack_from('<I', data, 4)[0]]
    if data[:2] == b'MZ':
        offset = struct.unpack_from('<I', data, 60)[0]
        if data[offset:offset + 4] == b'PE\0\0':
            return 'win32', {0x8664: 'x64', 0xaa64: 'arm64'}[struct.unpack_from('<H', data, offset + 4)[0]]
    raise ValueError('Unknown native binary header')


def run(args, cwd=ROOT, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def validate_pkg_info(text, tag):
    info = ET.fromstring(text)
    bundle = info.find('bundle')
    if (info.get('identifier') != 'com.aethermesh-ai.eidolon'
            or info.get('version') != tag.removeprefix('alpha-v')
            or info.get('install-location') != '/Applications'
            or bundle is None or bundle.get('path') not in ('Eidolon.app', './Eidolon.app')
            or info.get('relocatable') != 'false' or list(info.findall('relocate/bundle'))):
        raise ValueError('PKG must install non-relocatable Eidolon.app into /Applications')


def packaged_pty_smoke(executable, pty_root, temp):
    # Windows GUI-subsystem Electron may not expose console output to the runner.
    # Persist the last stage synchronously, including before native calls that
    # could block the JS watchdog; Python's unchanged 30s bound covers those.
    evidence = temp / 'pty-smoke.json'
    evidence.write_text(json.dumps({'stage': 'launching'}), encoding='utf-8')
    smoke_env = dict(os.environ, ELECTRON_RUN_AS_NODE='1',
                     EIDOLON_TEST_PTY=str(pty_root), EIDOLON_TEST_RESULT=str(evidence))
    smoke = """
const fs = require('fs');
const state = {platform: process.platform, arch: process.arch,
  electron: process.versions.electron, abi: process.versions.modules, output: ''};
const record = stage => {
  state.stage = stage;
  fs.writeFileSync(process.env.EIDOLON_TEST_RESULT, JSON.stringify(state));
};
record('started');
let child;
const timer = setTimeout(() => {
  state.waitingAt = state.stage;
  record('timeout');
  try { if (child) child.kill(); } finally { process.exit(2); }
}, 15000);
process.on('uncaughtException', error => {
  state.waitingAt = state.stage;
  state.error = String(error.stack || error).slice(0, 4096);
  record('error');
  process.exit(1);
});
record('requiring');
const pty = require(process.env.EIDOLON_TEST_PTY);
record('spawning');
const win = process.platform === 'win32';
child = pty.spawn(win ? 'cmd.exe' : '/bin/sh',
  win ? ['/d', '/s', '/c', 'echo EIDOLON_RELEASE_PTY'] : ['-c', 'printf EIDOLON_RELEASE_PTY'],
  {env: process.env, cols: 80, rows: 24});
record('spawned');
child.onData(data => {
  state.output = (state.output + data).slice(0, 4096);
  record('data');
});
child.onExit(({exitCode}) => {
  clearTimeout(timer);
  state.exitCode = exitCode;
  const passed = exitCode === 0 && state.output.includes('EIDOLON_RELEASE_PTY');
  record(passed ? 'passed' : 'failed');
  // This disposable ABI/spawn probe is complete; do not wait on PTY handles.
  // Persist the result before exiting: console.log can be lost on Windows.
  process.exit(passed ? 0 : 3);
});
"""
    try:
        subprocess.run([str(executable), '-e', smoke], cwd=temp, env=smoke_env, check=True, timeout=30)
    finally:
        print('Packaged PTY smoke evidence: ' + evidence.read_text(encoding='utf-8'), flush=True)
    result = json.loads(evidence.read_text(encoding='utf-8'))
    if (result.get('stage') != 'passed' or result.get('exitCode') != 0
            or 'EIDOLON_RELEASE_PTY' not in result.get('output', '')):
        raise ValueError('Packaged Electron exited without verified PTY success')
    print('Packaged Electron/node-pty ABI and spawn smoke passed', flush=True)


def package(tag, platform, arch, temp):
    variant = next(v for v in VARIANTS if v[:2] == (platform, arch))
    actual = subprocess.check_output(['node', '-p', 'process.platform+"/"+process.arch'], text=True).strip()
    if actual != platform + '/' + arch:
        raise ValueError('Must build on native host/Node architecture: ' + actual)
    config = json.loads((DESKTOP / 'package.json').read_text())['build']
    config['artifactName'] = f'{variant[2]}_{arch}_{tag}.${{ext}}'
    output = temp / 'package'
    output.mkdir(parents=True)
    config['directories'] = {'output': str(output)}
    config['publish'] = None
    if platform == 'darwin':
        config['mac']['identity'] = '-'  # ad-hoc only, no invented Developer ID
        config['mac']['notarize'] = False
        config.pop('afterSign', None)
        config['pkg'] = {'installLocation': '/Applications', 'isRelocatable': False,
                         'isVersionChecked': True, 'overwriteAction': 'upgrade'}
    if platform == 'win32':
        config.setdefault('nsis', {}).update({'useZip': False, 'differentialPackage': False,
                                             'runAfterFinish': False})
    cfg = temp / 'electron-builder.json'
    cfg.write_text(json.dumps(config))
    target = {'darwin': '--mac', 'linux': '--linux', 'win32': '--win'}[platform]
    # Invoke npm lifecycle so the existing mac binary patch is applied too.
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    format_target = {'darwin': 'pkg', 'linux': 'AppImage', 'win32': 'nsis'}[platform]
    run([npm, 'run', 'builder', '--', '--config', str(cfg), target, format_target, '--' + arch, '--publish', 'never'], cwd=DESKTOP)
    name = f'{variant[2]}_{arch}_{tag}.{variant[3]}'
    artifact = output / name
    if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size == 0:
        raise ValueError('Expected package missing: ' + name)
    unpacked = temp / 'verify-installer'
    if platform == 'darwin':
        run(['pkgutil', '--expand-full', str(artifact), str(unpacked)])
        infos = list(unpacked.rglob('PackageInfo'))
        if len(infos) != 1:
            raise ValueError('Expected exactly one PKG component')
        validate_pkg_info(infos[0].read_text(), tag)
    elif platform == 'linux':
        data = artifact.read_bytes()
        if data[8:11] != b'AI\x02' or binary_target(data) != (platform, arch):
            raise ValueError('Expected native Type 2 AppImage')
        artifact.chmod(0o755)
        unpacked.mkdir()
        run([str(artifact), '--appimage-extract'], cwd=unpacked)
        appdir = unpacked / 'squashfs-root'
        if not (appdir / 'AppRun').is_file() or not list(appdir.glob('*.desktop')):
            raise ValueError('AppImage launcher/desktop integration missing')
    else:
        # NSIS bootstrap is x86 even for native ARM64 payloads. Inspect the
        # embedded archive, not the bootstrap PE architecture or builder folder.
        seven = shutil.which('7z')
        if not seven:
            raise ValueError('NSIS inspection requires full 7-Zip (7z), not 7za')
        outer = temp / 'nsis-container'
        run([seven, 't', str(artifact)])
        run([seven, 'x', str(artifact), '-o' + str(outer), '-y'])
        payloads = list(outer.rglob('app-*.7z'))
        if len(payloads) != 1:
            raise ValueError('Expected one embedded NSIS application archive')
        run([seven, 't', str(payloads[0])])
        run([seven, 'x', str(payloads[0]), '-o' + str(unpacked), '-y'])
    # Validate packaged (not source) Electron and every unpacked native module.
    executables = list(unpacked.rglob('Contents/MacOS/Eidolon')) if platform == 'darwin' else list(unpacked.rglob('Eidolon.exe' if platform == 'win32' else 'Eidolon'))
    executables = [p for p in executables if p.is_file()]
    if len(executables) != 1:
        raise ValueError('Expected one packaged Electron executable')
    native = list(unpacked.rglob('*.node'))
    if not native or not any('node-pty' in p.parts for p in native):
        raise ValueError('Packaged node-pty native payload missing')
    for binary in [*executables, *native]:
        if binary_target(binary.read_bytes()) != (platform, arch):
            raise ValueError('Wrong native architecture: ' + str(binary))
    if platform == 'darwin':
        run(['codesign', '--verify', '--deep', '--strict', str(executables[0].parents[2])])
    stamp_paths = [p for p in unpacked.rglob('install-stamp.json') if p.parent.name.lower() == 'resources']
    if len(stamp_paths) != 1:
        raise ValueError('Expected one packaged install stamp')
    stamp = json.loads(stamp_paths[0].read_text())
    if (stamp['commit'] != os.environ['GITHUB_SHA'] or stamp['version'] != tag.removeprefix('alpha-v')
            or stamp['channel'] != 'alpha' or stamp['repository'] != 'AetherMesh-AI/Eidolon'):
        raise ValueError('Packaged install stamp must match source SHA/version/channel/repository')
    if os.environ.get('GITHUB_ACTIONS') == 'true' and stamp['dirty'] is not False:
        raise ValueError('Release requires a clean source tree at build time')
    # Electron Node mode loads the packaged addon with Electron's actual ABI,
    # without starting the app/UI or contacting model/backend services.
    pty_roots = list(unpacked.rglob('app.asar.unpacked/dist/node_modules/node-pty'))
    if len(pty_roots) != 1:
        raise ValueError('Expected exactly one packaged node-pty module')
    packaged_pty_smoke(executables[0], pty_roots[0], temp)
    assets = temp / 'assets'; assets.mkdir()
    artifact.rename(assets / name)
    print(json.dumps(file_record(assets / name)))


def main():
    tag = os.environ['RELEASE_TAG']; body = os.environ['RELEASE_CHANGELOG']
    version = json.loads((DESKTOP / 'package.json').read_text())['version']
    validate_inputs(tag, body, version)
    command = sys.argv[1]
    if command == 'preflight':
        absent(API(), tag)
    elif command == 'package':
        package(tag, os.environ['TARGET_PLATFORM'], os.environ['TARGET_ARCH'], Path(os.environ['RUNNER_TEMP']) / 'eidolon-release')
    elif command == 'publish':
        # Only materialized here, outside checkout; exact input bytes, no shell parsing.
        with tempfile.TemporaryDirectory(prefix='eidolon-notes-', dir=os.environ['RUNNER_TEMP']) as td:
            notes = Path(td) / 'notes.md'
            notes.write_text(body, encoding='utf-8', newline='')
            with notes.open(encoding='utf-8', newline='') as source:
                publish(API(), Path(os.environ['RELEASE_ASSETS']), tag, os.environ['GITHUB_SHA'], source.read())
    else:
        raise ValueError('Unknown command')


if __name__ == '__main__':
    main()
