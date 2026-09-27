import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'vitest'
import { activeHermesRoot } from './ahmer-runtime-root'

test('a staged personal runtime owns code paths while the original home stays in place', () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'ahmer-root-'))
  try {
    const home = path.join(work, 'home')
    const root = path.join(work, 'release/hermes-agent')
    fs.mkdirSync(path.join(home, 'hermes-agent/.git'), {recursive:true})
    fs.mkdirSync(root, {recursive:true})
    fs.writeFileSync(path.join(root, 'Hermes-Ahmer.md'), 'personal fork')
    assert.equal(activeHermesRoot(home, root), path.join(home, 'hermes-agent'))
    fs.writeFileSync(path.join(root, '..', 'ahmer-release.json'), '{}')
    assert.equal(activeHermesRoot(home, root), root)
    assert.ok(fs.existsSync(path.join(home, 'hermes-agent/.git')))
    assert.equal(activeHermesRoot(home), path.join(home, 'hermes-agent'))
  } finally {
    fs.rmSync(work, {recursive:true, force:true})
  }
})
