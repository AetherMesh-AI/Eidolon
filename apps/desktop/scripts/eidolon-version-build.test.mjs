import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { writeBuildStamp } from './write-build-stamp.mjs'
import { buildArguments } from './run-electron-builder.mjs'
import { readInstallStampFromPaths, formatInstallVersion } from '../electron/install-stamp.ts'

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'version-build-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  fs.mkdirSync(path.join(root, 'hermes_cli'))
  fs.copyFileSync(new URL('../../../hermes_cli/eidolon_version.py', import.meta.url), path.join(root, 'hermes_cli/eidolon_version.py'))
  fs.writeFileSync(path.join(root, '.gitignore'), 'hermes_cli/_build_identity.json\napps/desktop/build/\n')
  const git = (...args) => execFileSync('/usr/bin/git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
  git('init', '-b', 'main')
  git('add', '.')
  git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'anchor')
  git('tag', 'alpha-v0.1.0')
  const commit = () => git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-m', 'advance')
  return { root, git, commit, stampPath: path.join(root, 'apps/desktop/build/install-stamp.json') }
}

test('real generator -> stamp -> desktop display -> numeric packager override', t => {
  const { root, git, commit, stampPath } = fixture(t)
  commit(); commit()
  const payload = writeBuildStamp({ repoRoot: root })
  assert.equal(payload.version, '0.1.2')
  assert.equal(payload.distance, 2)
  assert.equal(git('status', '--porcelain'), '')
  const stamp = readInstallStampFromPaths([stampPath])
  assert.match(formatInstallVersion(stamp), /^0\.1\.2 alpha/)
  assert.ok(formatInstallVersion(stamp).includes(payload.commit.slice(0, 12)))
  assert.doesNotMatch(formatInstallVersion(stamp), /unverified|unknown|dirty/)
  const args = buildArguments({ repoRoot: root, stampPath, argv: ['--dir'] })
  assert.ok(args.includes('-c.extraMetadata.version=0.1.2'))
  assert.deepEqual(args.slice(-2), ['--publish', 'never'])
  // Pure argument generation never resolves or invokes electron-builder.
  assert.throws(() => buildArguments({ repoRoot: root, stampPath, argv: ['-c.extraMetadata.version=9.9.9'] }), /override/)
  commit()
  assert.throws(() => buildArguments({ repoRoot: root, stampPath }), /stale|mismatch/i)
})

test('missing, legacy, fallback and malformed versions cannot package', t => {
  const { root, stampPath } = fixture(t)
  assert.throws(() => buildArguments({ repoRoot: root, stampPath }))
  const valid = writeBuildStamp({ repoRoot: root })
  for (const change of [{ versionSource: 'fallback' }, { version: '99.0.0' }, { distance: true }, { shortCommit: 'wrong' }, { baseCommit: 'z'.repeat(40) }]) {
    fs.writeFileSync(stampPath, JSON.stringify({ ...valid, ...change }))
    assert.match(formatInstallVersion(readInstallStampFromPaths([stampPath])), /unverified/)
    assert.throws(() => buildArguments({ repoRoot: root, stampPath }))
  }
  fs.writeFileSync(stampPath, JSON.stringify({ commit: valid.commit, dirty: false }))
  assert.match(formatInstallVersion(readInstallStampFromPaths([stampPath])), /unverified/)
  assert.throws(() => buildArguments({ repoRoot: root, stampPath }))
})

test('Git-less generated identity reuses Python stamp; CI SHA never supplies ancestry', t => {
  const { root, stampPath } = fixture(t)
  const python = process.env.HERMES_PYTHON || 'python3'
  execFileSync(python, [path.join(root, 'hermes_cli/eidolon_version.py'), '--repo-root', root, '--output', path.join(root, 'hermes_cli/_build_identity.json')])
  fs.rmSync(path.join(root, '.git'), { recursive: true })
  assert.equal(writeBuildStamp({ repoRoot: root }).versionSource, 'stamp')
  assert.ok(buildArguments({ repoRoot: root, stampPath }).includes('-c.extraMetadata.version=0.1.0'))
  fs.rmSync(path.join(root, 'hermes_cli/_build_identity.json'))
  const payload = writeBuildStamp({ repoRoot: root, env: { ...process.env, GITHUB_SHA: 'a'.repeat(40) } })
  assert.equal(payload.versionSource, 'fallback')
  assert.match(formatInstallVersion(readInstallStampFromPaths([stampPath])), /unverified/)
  assert.throws(() => buildArguments({ repoRoot: root, stampPath }))
})
