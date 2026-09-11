import fs from 'node:fs'

const INSTALL_STAMP_SCHEMA_VERSION = 1

/** Packaged location first, dev build second; unknown dirtiness stays unknown. */
export function readInstallStampFromPaths(candidates: string[], warn = console.warn) {
  for (const p of candidates) {
    try {
      const parsed = JSON.parse(fs.readFileSync(p, 'utf8'))
      if (parsed && typeof parsed === 'object' && typeof parsed.commit === 'string' && parsed.commit.length >= 7) {
        if (parsed.schemaVersion !== INSTALL_STAMP_SCHEMA_VERSION) {
          warn(`[hermes] install-stamp.json schemaVersion ${parsed.schemaVersion} != expected ${INSTALL_STAMP_SCHEMA_VERSION}; ignoring`)
          continue
        }
        return Object.freeze({
          schemaVersion: parsed.schemaVersion,
          commit: parsed.commit,
          branch: parsed.branch || null,
          builtAt: parsed.builtAt || null,
          dirty: typeof parsed.dirty === 'boolean' ? parsed.dirty : null,
          source: parsed.source || null,
          path: p
        })
      }
    } catch (e) {
      warn(`[hermes] install-stamp.json found at ${p} , but parsing failed with ${e}`)
    }
  }
  return null
}

export function formatInstallStamp(stamp: { commit: string; branch?: string | null; dirty?: boolean | null; source?: string | null }) {
  const dirty = stamp.dirty === true ? ' [DIRTY]' : stamp.dirty === false ? '' : ' [DIRTY UNKNOWN]'
  return `${stamp.commit.slice(0, 12)}${stamp.branch ? ` (${stamp.branch})` : ''}${dirty} from ${stamp.source || 'unknown'}`
}

/** Shared by the renderer version IPC, including absent/legacy stamp cases. */
export function formatInstallVersion(stamp: { commit?: string; dirty?: boolean | null } | null) {
  const commit = stamp?.commit
  const exact = typeof commit === 'string' && /^[0-9a-f]{40}$/.test(commit) && !/^0+$/.test(commit)
  const dirty = stamp?.dirty === true ? ' (dirty source)' : stamp?.dirty === false ? '' : ' (source status unknown)'
  return `0.1.0 alpha · ${exact ? commit : 'unknown commit'}${dirty}`
}
