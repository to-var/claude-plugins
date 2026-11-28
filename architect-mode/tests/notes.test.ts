import { describe, expect, test } from 'claude-code/testing'

import { clean, defuse, emptyPane, fenced, logEntry, logPath, noteProblem, readNote, table, withNote } from '../hooks/notes'

const NOTE = { kind: 'decision', title: 'New file', text: 'The lock stays small.', sources: ['hooks/register.tsx:9'] }

describe('reading a note', () => {
  test('a good note passes', () => {
    expect(readNote(NOTE)).toEqual(NOTE)
  })

  test('a note without a source is refused', () => {
    for (const sources of [undefined, [], ['trust me'], ['http://a.dev'], ['file:///etc/passwd'], ['https://a.dev/x y']]) {
      expect(readNote({ ...NOTE, sources })).toBeNull()
      expect(noteProblem({ ...NOTE, sources })).toContain('source')
    }
  })

  test('https links and file:line are sources, on both path styles', () => {
    const sources = ['https://nextjs.org/docs', 'src\\app\\page.tsx:3', 'C:\\p\\a.ts:12']
    expect(readNote({ ...NOTE, sources })?.sources).toEqual(sources)
  })

  test('a wrong kind, an empty field or a long field is refused', () => {
    for (const bad of [{ kind: 'order' }, { title: ' ' }, { text: 3 }, { title: 'a'.repeat(81) }, { text: 'a'.repeat(501) }]) {
      expect(readNote({ ...NOTE, ...bad })).toBeNull()
    }
    expect(readNote({ ...NOTE, kind: 'tree', text: 'a'.repeat(3000) })).not.toBeNull()
  })

  test('a source cannot hide a link or its real host', () => {
    for (const source of [
      'https://[docs](file:///C:/x)',
      'https://a.dev/(x)',
      'https://docs.python.org@evil.dev',
      'https://a.dev/`x',
      'https://a.dev/|x',
      'https://a.dev/\u202Ex',
      `https://a.dev/${'a'.repeat(300)}`,
      'a`b.ts:1',
    ]) {
      expect(readNote({ ...NOTE, sources: [source] })).toBeNull()
    }
    expect(readNote({ ...NOTE, sources: ['a.ts:1', 'a.ts:2', 'a.ts:3', 'a.ts:4'] })).toBeNull()
    const fine = ['https://docs.python.org:443/3/library/re.html?q=a_b%20c#re.sub']
    expect(readNote({ ...NOTE, sources: fine })?.sources).toEqual(fine)
  })

  test('hidden characters go, line breaks and indentation stay', () => {
    expect(clean('a\u202Eb\u0007c\r\n  d\te')).toBe('abc\n  d\te')
    expect(readNote({ ...NOTE, kind: 'tree', text: 'hooks/\n  pane.tsx' })?.text).toBe('hooks/\n  pane.tsx')
  })
})

describe('model text on screen', () => {
  test('a link cannot hide where it goes', () => {
    expect(defuse('[docs](https://evil.dev)')).toBe('[docs] (https://evil.dev)')
    expect(defuse('[x]: https://evil.dev')).toBe('[x] : https://evil.dev')
  })

  test('only https stays a link', () => {
    const out = defuse('http://a.dev FILE:///c www.a.dev https://ok.dev <a href=x>')
    for (const gone of ['http://', 'FILE://', 'www.a', '<a']) expect(out).not.toContain(gone)
    expect(out).toContain('https://ok.dev')
  })

  test('an underscore or a slash does not keep a link alive', () => {
    const out = defuse('_http://a.dev _www.b.dev /www.c.dev xFILE:///d')
    for (const gone of ['http://', 'www.b', 'www.c', 'FILE://']) expect(out).not.toContain(gone)
    expect(defuse('https://www.ok.dev')).toBe('https://www.ok.dev')
  })

  test('stacked heading marks and tabbed lists are not headings', () => {
    expect(defuse('# # Approved')).toBe('Approved')
    expect(defuse('-\t# Approved')).toBe('-\tApproved')
    expect(defuse('# > # Approved')).toBe('> Approved')
    expect(defuse('# - # Approved')).toBe('- Approved')
  })

  test('a tree cannot close its block', () => {
    expect(fenced('a\n```\n# b\n````').match(/```/g)?.length).toBe(2)
  })

  test('it cannot fake a heading, and tables stay', () => {
    expect(defuse('# Approved\n> ## Also\nTitle\n===')).toBe('Approved\n> Also\nTitle\n')
    expect(defuse('| a | b |\n|---|---|')).toBe('| a | b |\n|---|---|')
  })

  test('a note stays in its own table cell', () => {
    const out = table('Decision', [{ ...NOTE, kind: 'decision', title: 'a|b', text: 'one\ntwo' }])
    expect(out.split('\n').length).toBe(3)
    expect(out).toContain('| a\\|b | one two | `hooks/register.tsx:9` |')
  })
})

describe('pane state', () => {
  test('a new tree replaces the old one and old decisions drop off', () => {
    let pane = emptyPane()
    for (let i = 0; i < 25; i += 1) pane = withNote(pane, { ...NOTE, kind: 'decision', title: `d${i}` })
    pane = withNote(pane, { ...NOTE, kind: 'tree', title: 'one' })
    pane = withNote(pane, { ...NOTE, kind: 'tree', title: 'two' })
    expect(pane.decisions.length).toBe(20)
    expect(pane.decisions[0]!.title).toBe('d5')
    expect(pane.tree?.title).toBe('two')
  })
})

describe('the log', () => {
  test('the same project has one key on both path styles', () => {
    expect(logPath('/data', 'C:\\p\\x')).toBe(logPath('/data', 'C:/p/x'))
    expect(logPath('/data', 'C:/p/x')).toBe('/data/projects/C-p-x/notes.md')
    expect(logPath('/data', '/p/../../y')).toBe('/data/projects/-p-y/notes.md')
  })

  test('text cannot forge another entry', () => {
    const entry = logEntry('decision', 'a\n## b', 'x\n## forged', ['a.ts:1'])
    expect(entry.match(/^## /gm)?.length).toBe(1)
  })
})
