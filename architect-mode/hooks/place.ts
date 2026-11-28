// Where a path really lands, or null when the lock cannot tell. A null path is
// refused during a run, so every doubt ends here.

const DRIVE = /^[a-z]:/i

function isPlaceable(path: string, root: string): boolean {
  if (/^[a-z]:(?![\\/])/i.test(path)) return false // drive-relative "C:a"
  if (/^[\\/]{2}/.test(path)) return false // network and device paths
  const isWindows = DRIVE.test(root)
  if (isWindows ? !DRIVE.test(path) : !path.startsWith('/')) return false
  const parts = path.split(isWindows ? /[\\/]/ : '/')
  if (parts.at(-1) === '' || parts.some(part => part === '..' || part === '.')) return false
  // Windows drops a trailing dot or space, and "NAME~1" is a short alias.
  return !isWindows || !parts.some(part => /[. ]$|~\d+(\.[^.]{0,3})?$/.test(part))
}

async function stat($: any, path: string): Promise<{ realPath?: string } | undefined> {
  return $.fs.stat(path, { resolve: true }).catch(() => undefined)
}

export async function place($: any, path: string, root: string): Promise<string | null> {
  if (!isPlaceable(path, root)) return null
  const own = await stat($, path)
  if (own !== undefined) return own.realPath ?? null
  // A new file: place its nearest existing folder, then add the rest.
  for (let cut = path.length - 1; cut >= 0; cut--) {
    if (path[cut] !== '/' && path[cut] !== '\\') continue
    // The separator stays, so a drive or file system root stays that root.
    const folder = await stat($, path.slice(0, cut + 1))
    if (folder === undefined) continue
    if (folder.realPath === undefined) return null
    return `${folder.realPath.replace(/[\\/]$/, '')}/${path.slice(cut + 1).replace(/\\/g, '/')}`
  }
  return null
}
