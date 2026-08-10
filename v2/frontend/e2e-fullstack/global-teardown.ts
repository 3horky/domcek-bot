import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

export default function globalTeardown() {
  const launcher = fileURLToPath(new URL('../../scripts/run_browser_e2e_api.sh', import.meta.url))
  execFileSync(launcher, ['cleanup'], { stdio: 'inherit' })
}
