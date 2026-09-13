// Resolve electronDist at runtime (#38673, #47917): electron-builder 26.8.x can
// re-unpack a broken Electron.app; reusing the installed dist dodges that.
// npm workspace hoisting is non-deterministic — require.resolve finds electron
// wherever it landed. Dist present → -c.electronDist=<abs>/dist; absent → let
// electron-builder fetch via @electron/get (electronVersion + ELECTRON_MIRROR).

import fs from "node:fs"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { createRequire } from "node:module"

const require = createRequire(import.meta.url)

function electronDistDir() {
  try {
    return path.join(path.dirname(require.resolve("electron/package.json")), "dist")
  } catch {
    return null
  }
}

function distBinary(dist) {
  if (process.platform === "darwin") {
    return path.join(dist, "Electron.app", "Contents", "MacOS", "Electron")
  }
  if (process.platform === "win32") {
    return path.join(dist, "electron.exe")
  }
  return path.join(dist, "electron")
}

function electronBuilderCli() {
  const pkgJson = require.resolve("electron-builder/package.json")
  const bin = require(pkgJson).bin
  const rel = typeof bin === "string" ? bin : bin["electron-builder"]
  return path.join(path.dirname(pkgJson), rel)
}

import { isMain } from './utils.mjs'
import { resolveBuildIdentity } from './write-build-stamp.mjs'

/** Refuse fallback, stale, or hand-edited stamps before loading the packager. */
export function buildArguments({
  repoRoot = path.resolve(import.meta.dirname, '../../..'),
  stampPath = path.join(repoRoot, 'apps/desktop/build/install-stamp.json'),
  argv = process.argv.slice(2),
} = {}) {
  const stamp = JSON.parse(fs.readFileSync(stampPath, 'utf8'))
  const current = resolveBuildIdentity({ repoRoot })
  if (!['git-derived', 'stamp'].includes(current.versionSource) ||
      !['git-derived', 'stamp'].includes(stamp.versionSource)) {
    throw new Error('Native packaging requires a verified Git-derived build identity')
  }
  for (const key of ['schemaVersion', 'version', 'channel', 'repository', 'updateBranch',
    'commit', 'shortCommit', 'dirty', 'baseTag', 'baseCommit', 'distance']) {
    if (stamp[key] !== current[key]) throw new Error(`Stale or conflicting build identity: ${key}`)
  }
  if (argv.some(arg => /(?:extraMetadata\.(?:version|channel)|buildVersion)/.test(arg))) {
    throw new Error('Build identity overrides are owned by the generated stamp')
  }
  return [...argv, `-c.extraMetadata.version=${current.version}`, '--publish', 'never']
}

export function runBuilder({ spawn = spawnSync, ...options } = {}) {
  // Validate first: no packager resolution, download, or launch on refusal.
  const args = buildArguments(options)
  const dist = electronDistDir()
  if (dist && fs.existsSync(distBinary(dist))) {
    args.push(`-c.electronDist=${dist}`)
  } else {
    console.warn('[run-electron-builder] no local electron dist; electron-builder may fetch it.')
  }
  const result = spawn(process.execPath, [electronBuilderCli(), ...args], { stdio: 'inherit' })
  if (result.error) throw result.error
  return result.status == null ? 1 : result.status
}

if (isMain(import.meta.url)) {
  try { process.exitCode = runBuilder() }
  catch (error) {
    console.error(`[run-electron-builder] ${error.message}`)
    process.exitCode = 1
  }
}
