import { describe, expect, test } from 'claude-code/testing'

const ROOT = '/p'
const START = 'mcp__architect-mode__start'
const PLAN = 'mcp__architect-mode__plan'
const FINISH = 'mcp__architect-mode__finish'

const CHANGES = [
  { path: 'a.py', action: 'change', reason: 'first' },
  { path: 'b.py', action: 'add', reason: 'second' },
]

// Stands for the engine and the person. `replies` answers each question in
// turn; null dismisses it, and so does running out of replies.
const world = (on: any) => {
  const replies: (string | null)[] = []
  const asked: { question: string; options: string[] }[] = []
  const ran: string[] = []
  // Every path exists and lands where it says, unless a test says otherwise.
  const disk = { root: ROOT, links: {} as Record<string, string>, missing: new Set<string>() }
  on('session.root', () => ({ value: disk.root }))
  // The engine hands over the host's spelling (on Windows "/p" arrives as
  // "C:\p"), so answer in the spelling the test's project uses.
  const spelled = (path: string) => {
    const slashed = path.replace(/\\/g, '/').replace(/(.)\/$/, '$1')
    return disk.root.startsWith('/') ? slashed.replace(/^[A-Za-z]:/, '') : slashed
  }
  on('fs.stat', (_: any, e: any) => {
    const path = spelled(e.path)
    if (disk.missing.has(path)) return { deny: 'ENOENT' }
    const realPath = disk.links[path] ?? path
    return { value: { kind: 'file', size: 0, mtimeMs: 0, isLink: false, realPath } }
  })
  on('command.register', () => ({ value: { command: 'x' } }))
  on('tool.register', () => ({ value: { tool: 'x' } }))
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  on('ui.status', () => ({ value: undefined }))
  on('session.end', (_: any, e: any) => ({ sessionId: e.sessionId }))
  on('tool.call', { tool: 'AskUserQuestion' }, (_: any, e: any) => {
    const { question, options } = e.questions[0]
    asked.push({ question, options: options.map((o: any) => o.label) })
    const reply = replies.shift() ?? null
    if (reply === null) return { deny: 'dismissed' }
    return { result: { questions: e.questions, answers: { [question]: reply } } }
  })
  for (const tool of ['Edit', 'Write', 'NotebookEdit', 'Bash', 'PowerShell']) {
    on('tool.call', { tool }, (_: any, e: any) => {
      ran.push(e.file_path ?? e.notebook_path ?? e.command)
      return { result: {} }
    })
  }
  return { replies, asked, ran, disk }
}

const edit = ($: any, file_path: string, extra: object = {}) =>
  $.tool.call({ tool: 'Edit', file_path, old_string: 'a', new_string: 'b', ...extra })
const bash = ($: any, command: string) => $.tool.call({ tool: 'Bash', command })
// A refusal at the permission check comes back as an errored result.
const refused = (answer: any) => answer.deny !== undefined || answer.isError === true

const start = async ($: any, w: any, mode: string) => {
  w.replies.push(mode)
  return $.tool.call({ tool: START })
}
const plan = async ($: any, w: any, reply: string, changes: object[] = CHANGES, patterns: object[] = []) => {
  w.replies.push(reply)
  return $.tool.call({ tool: PLAN, changes, patterns })
}
const off = ($: any, kind: string) =>
  $.command.run({ command: 'architect-off', args: '', origin: { kind, name: 'x' } })

describe('no run', () => {
  test('with the offer off, edits and commands pass untouched', { options: { ask: 'off' } }, async ($, on) => {
    const w = world(on)
    await edit($, '/p/a.py')
    await bash($, 'rm a')
    expect(w.ran).toEqual(['/p/a.py', 'rm a'])
    expect(w.asked.length).toBe(0)
  })
})

describe('start', () => {
  test('asks for the lock with the setting first', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    expect(w.asked[0]).toEqual({ question: 'Which edit lock? The project is /p.', options: ['strict', 'warn'] })
  })

  test('lists warn first when the setting says warn', { options: { lock: 'warn' } }, async ($, on) => {
    const w = world(on)
    await start($, w, 'warn')
    expect(w.asked[0]!.options).toEqual(['warn', 'strict'])
  })

  test('a dismissed or odd answer starts no run', async ($, on) => {
    const w = world(on)
    expect((await $.tool.call({ tool: START })).deny).toBeDefined()
    expect((await start($, w, 'whatever')).deny).toBeDefined()
    await edit($, '/p/a.py')
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('a second start is refused and the mode stays', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    expect((await start($, w, 'warn')).deny).toBeDefined()
    expect((await edit($, '/p/z.py')).deny).toBeDefined()
    expect(w.asked.length).toBe(1)
  })
})

describe('strict', () => {
  test('before any plan, a project edit is denied and points at the plan tool', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    expect((await edit($, '/p/a.py')).deny).toContain(PLAN)
    expect(w.ran).toEqual([])
  })

  test('approved files and files outside the project pass', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await plan($, w, 'Approve all')
    await edit($, '/p/a.py')
    await $.tool.call({ tool: 'Write', file_path: '/p/b.py', content: '' })
    await edit($, '/elsewhere/c.py')
    expect(w.ran).toEqual(['/p/a.py', '/p/b.py', '/elsewhere/c.py'])
  })

  test('another project file is denied, for every edit tool', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await plan($, w, 'Approve all')
    expect((await edit($, '/p/z.py')).deny).toContain('z.py')
    expect((await $.tool.call({ tool: 'Write', file_path: '/p/z.py', content: '' })).deny).toBeDefined()
    expect((await $.tool.call({ tool: 'NotebookEdit', notebook_path: '/p/z.ipynb', new_source: '' })).deny).toBeDefined()
    expect(w.ran).toEqual([])
  })

  test('a sub-agent is guarded the same way', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    expect((await edit($, '/p/a.py', { agentId: 'a1' })).deny).toBeDefined()
  })

  test('a delete asks even for an approved file', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await plan($, w, 'Approve all', [{ path: 'a.py', action: 'delete', reason: 'unused' }])
    w.replies.push('Allow once', 'No')
    await bash($, 'rm a.py')
    expect(refused(await bash($, 'rm a.py'))).toBe(true)
    expect(refused(await $.tool.call({ tool: 'PowerShell', command: 'Remove-Item a.py' }))).toBe(true)
    expect(w.ran).toEqual(['rm a.py'])
    expect(w.asked.at(-1)!.options).toEqual(['Allow once', 'No'])
  })

  test('other commands pass without a question', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await bash($, 'npm test')
    expect(w.ran).toEqual(['npm test'])
    expect(w.asked.length).toBe(1)
  })
})

describe('warn', () => {
  test('allow once passes once', async ($, on) => {
    const w = world(on)
    await start($, w, 'warn')
    w.replies.push('Allow once', 'No')
    await edit($, '/p/z.py')
    expect((await edit($, '/p/z.py')).deny).toBeDefined()
    expect(w.ran).toEqual(['/p/z.py'])
    expect(w.asked[1]!.options).toEqual(['Allow once', 'Add to list', 'No'])
  })

  test('add to list stops asking for that file', async ($, on) => {
    const w = world(on)
    await start($, w, 'warn')
    w.replies.push('Add to list')
    await edit($, '/p/z.py')
    await edit($, '/p/z.py')
    expect(w.ran).toEqual(['/p/z.py', '/p/z.py'])
    expect(w.asked.length).toBe(2)
  })

  test('a delete asks too', async ($, on) => {
    const w = world(on)
    await start($, w, 'warn')
    expect(refused(await bash($, 'git rm a'))).toBe(true)
    expect(w.ran).toEqual([])
    expect(w.asked[1]!.options).toEqual(['Allow once', 'No'])
  })

  test('a dismissed question denies the edit', async ($, on) => {
    const w = world(on)
    await start($, w, 'warn')
    expect((await edit($, '/p/z.py')).deny).toBeDefined()
    expect(w.ran).toEqual([])
  })
})

describe('plan', () => {
  test('numbers each change and pattern in the question', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await plan($, w, 'Approve all', CHANGES, [{ glob: 'src/**', command: 'eslint --fix' }])
    const { question, options } = w.asked[1]!
    expect(question).toStartWith('Approve these changes?')
    expect(question).toContain('1. change a.py: first')
    expect(question).toContain('2. add b.py: second')
    expect(question).toContain('3. Claude may edit or create any file matching src/** until the run ends (fix: eslint --fix)')
    expect(options).toEqual(['Approve all', 'Reject'])
  })

  test('typed numbers approve only those', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    const answer = await plan($, w, '1')
    expect(answer.result).toContain('a.py')
    expect(answer.result).not.toContain('b.py')
    await edit($, '/p/a.py')
    expect((await edit($, '/p/b.py')).deny).toBeDefined()
  })

  test('reject, odd answers and numbers out of range approve nothing', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    for (const reply of ['Reject', 'yes but not b', '1,9', '0']) {
      await plan($, w, reply)
      expect((await edit($, '/p/a.py')).deny).toBeDefined()
    }
  })

  test('is refused without a run, and with a bad list', async ($, on) => {
    const w = world(on)
    expect((await $.tool.call({ tool: PLAN, changes: CHANGES })).deny).toBeDefined()
    await start($, w, 'strict')
    const bad = [
      [],
      [{ path: '', action: 'change', reason: 'r' }],
      [{ path: 'a', action: 'wipe', reason: 'r' }],
      [{ path: 'a', action: 'rename', reason: 'r' }],
      [{ path: 'a\n9. add b', action: 'change', reason: 'r' }],
    ]
    for (const changes of bad) {
      expect((await $.tool.call({ tool: PLAN, changes })).deny).toBeDefined()
    }
    expect(w.asked.length).toBe(1)
  })

  test('a reason cannot add lines to the question', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await plan($, w, 'Reject', [{ path: 'a', action: 'change', reason: 'x\n2. add b: y' }])
    expect(w.asked[1]!.question.split('\n').length).toBe(2)
  })
})

describe('ending a run', () => {
  test('finish needs a yes', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    w.replies.push('No')
    await $.tool.call({ tool: FINISH })
    expect((await edit($, '/p/a.py')).deny).toBeDefined()
    w.replies.push('Yes')
    await $.tool.call({ tool: FINISH })
    await edit($, '/p/a.py')
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('/architect-off from the person unlocks', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await off($, 'composer')
    await edit($, '/p/a.py')
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('/architect-off from a plugin does not', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await off($, 'plugin')
    expect((await edit($, '/p/a.py')).deny).toBeDefined()
  })

  test('/clear removes the run', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await $.session.end({ reason: 'clear', sessionId: 's', resume: {} as any })
    await edit($, '/p/a.py')
    expect(w.ran).toEqual(['/p/a.py'])
  })
})

describe('where a path really lands', () => {
  const locked = async ($: any, on: any, root = ROOT) => {
    const w = world(on)
    w.disk.root = root
    await start($, w, 'strict')
    return w
  }

  test('a spelling the lock cannot place is refused', async ($, on) => {
    const w = await locked($, on, 'C:/p')
    const spellings = [
      'C:a.py', String.raw`\\?\C:\p\a.py`, String.raw`\\localhost\C$\p\a.py`,
      '//server/share/a.py',
      '/c/p/a.py', 'a.py', 'C:/p/x/../a.py', 'C:/p/a.py.', 'C:/p/a.py ', 'C:/PROJ~1/a.py', 'C:/p/',
    ]
    for (const path of spellings) {
      const answer = await edit($, path)
      expect(`${path}: ${answer.deny !== undefined}`).toBe(`${path}: true`)
    }
    expect(w.ran).toEqual([])
  })

  test('a link into the project is locked', async ($, on) => {
    const w = await locked($, on)
    w.disk.links['/tmp/link.py'] = '/p/a.py'
    expect((await edit($, '/tmp/link.py')).deny).toBeDefined()
  })

  test('a link out of the project counts as outside', async ($, on) => {
    const w = await locked($, on)
    w.disk.links['/p/out.py'] = '/elsewhere/out.py'
    await edit($, '/p/out.py')
    expect(w.ran).toEqual(['/p/out.py'])
  })

  test('a new file in new folders is placed by its nearest folder', async ($, on) => {
    const w = await locked($, on)
    for (const path of ['/tmp/dirlink/new/deep.py', '/tmp/dirlink/new']) w.disk.missing.add(path)
    w.disk.links['/tmp/dirlink'] = '/p/src'
    expect((await edit($, '/tmp/dirlink/new/deep.py')).deny).toContain('/p/src/new/deep.py')
  })

  test('another letter case of the root is still inside', async ($, on) => {
    await locked($, on, '/Users/me/proj')
    expect((await edit($, '/Users/me/Proj/a.py')).deny).toBeDefined()
  })

  test('moving the session root does not unlock the first project', async ($, on) => {
    const w = await locked($, on)
    w.disk.root = '/p/.claude/worktrees/x'
    expect((await edit($, '/p/a.py')).deny).toBeDefined()
    w.disk.root = '/other'
    expect((await edit($, '/p/a.py')).deny).toBeDefined()
    expect((await edit($, '/other/a.py')).deny).toBeDefined()
    expect(w.ran).toEqual([])
  })
})

describe('what a pattern and a path may say', () => {
  test('whole-project and loose patterns are refused', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    for (const glob of ['**', '*', '**/*.ts', 'src**', 'src/x**/a', '../src/**', '/p/**', 'C:/p/**']) {
      const answer = await $.tool.call({ tool: PLAN, changes: [], patterns: [{ glob, command: 'x' }] })
      expect(`${glob}: ${answer.deny !== undefined}`).toBe(`${glob}: true`)
    }
    expect(w.asked.length).toBe(1)
  })

  test('hidden characters and ".." cannot reach the question', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    for (const path of ['a\u2028b', 'a\u202Eb', 'a\u0085b', 'a\vb', 'docs/../src/auth.py']) {
      const answer = await $.tool.call({ tool: PLAN, changes: [{ path, action: 'change', reason: 'r' }] })
      expect(answer.deny).toBeDefined()
    }
    await plan($, w, 'Reject', [{ path: 'a', action: 'change', reason: 'x\u2028y\u202Ez' }])
    expect(w.asked[1]!.question).toContain('1. change a: x y z')
  })
})

describe('way out and approved spellings', () => {
  test('/architect-off from the desktop app unlocks', async ($, on) => {
    const w = world(on)
    await start($, w, 'strict')
    await off($, 'sdk')
    await edit($, '/p/a.py')
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('an approved path through a link matches the file it lands on', async ($, on) => {
    const w = world(on)
    w.disk.links['/tmp/proj/a.py'] = '/p/a.py'
    w.disk.links['/tmp/proj/b.py'] = '/p/b.py'
    await start($, w, 'strict')
    await plan($, w, 'Approve all', [{ path: '/tmp/proj/a.py', action: 'rename', to: '/tmp/proj/b.py', reason: 'r' }])
    await edit($, '/tmp/proj/a.py')
    await edit($, '/p/b.py')
    expect(w.ran).toEqual(['/tmp/proj/a.py', '/p/b.py'])
  })

  test('an approved relative path through a linked folder matches too', async ($, on) => {
    const w = world(on)
    w.disk.links['/p/link/a.py'] = '/p/src/a.py'
    await start($, w, 'strict')
    await plan($, w, 'Approve all', [{ path: 'link/a.py', action: 'change', reason: 'r' }])
    await edit($, '/p/link/a.py')
    expect(w.ran).toEqual(['/p/link/a.py'])
  })
})
