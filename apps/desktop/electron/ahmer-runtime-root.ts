import fs from 'node:fs'
import path from 'node:path'

/** Personal releases keep user data in the default home and code elsewhere. */
export function activeHermesRoot(home: string, override?: string): string {
  const root = override && path.resolve(override)
  if (root && fs.existsSync(path.join(root, 'Hermes-Ahmer.md')) &&
      fs.existsSync(path.join(root, '..', 'ahmer-release.json'))) {
    return root
  }
  return path.join(home, 'hermes-agent')
}
