import { logPath } from './notes'

// The only writer of the notes log. The log is never read back into the model.

// Well under what one read returns, so a rewrite cannot cut the file short.
const MAX = 2_000_000
// One write at a time: each one reads the file and writes it whole.
let queue: Promise<unknown> = Promise.resolve()

async function write($: any, root: string, entry: string): Promise<boolean> {
  const data = (await $.process.hookEnv()).CLAUDE_PLUGIN_DATA
  if (!data) return false
  const path = logPath(data, root)
  // The look comes first: a link that leads nowhere is not a missing file.
  // Any doubt other than "missing" throws, so nothing is written.
  const found = await $.fs.stat(path).catch((error: Error) => {
    if (/ENOENT/.test(error.message)) return null
    throw error
  })
  let old = '# Architect notes\n\n'
  if (found !== null) {
    if (found.isLink || found.size + entry.length > MAX) return false
    old = await $.fs.read(path)
    if (typeof old !== 'string') return false
  }
  await $.fs.write(path, old + entry)
  return true
}

// True when saved. Any failure leaves the file as it was.
export function appendLog($: any, root: string, entry: string): Promise<boolean> {
  const done = queue.then(() => write($, root, entry)).catch(() => false)
  queue = done
  return done
}
