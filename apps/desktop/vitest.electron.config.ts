import { defineConfig } from 'vitest/config'
import { electronNative } from './vitest.config'

// Same CI-classified project, without resolving unrelated renderer plugins.
export default defineConfig({ test: { projects: [electronNative] } })
