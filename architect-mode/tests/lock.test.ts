import { describe, expect, test } from 'claude-code/testing'

import { isApproved, isDelete, isInside, resolvePath } from '../hooks/lock'
import type { Run } from '../types'

const run: Run = {
  mode: 'strict',
  root: 'C:/p',
  patterns: [{ glob: 'src/**/*.ts', command: 'eslint --fix' }],
  changes: [
    { path: 'app/a.py', action: 'change', reason: 'r' },
    { path: 'old.py', to: 'new.py', action: 'rename', reason: 'r' },
  ],
}

describe('paths', () => {
  test('every Windows spelling of an approved file matches', () => {
    expect(isApproved('C:\\P\\app\\a.py', run, 'C:/p')).toBe(true)
    expect(isApproved('app/../app/a.py', run, 'C:/p')).toBe(true)
    expect(isApproved('app\\.\\a.py', run, 'C:\\p\\')).toBe(true)
    expect(resolvePath('c:\\P\\x\\..\\A.py', 'C:/p')).toBe('c:/p/a.py')
  })

  test('both ends of a rename and a pattern match', () => {
    expect(isApproved('C:/p/old.py', run, 'C:/p')).toBe(true)
    expect(isApproved('C:/p/new.py', run, 'C:/p')).toBe(true)
    expect(isApproved('C:/p/src/x/y.ts', run, 'C:/p')).toBe(true)
    expect(isApproved('C:/p/src/y.ts', run, 'C:/p')).toBe(true)
  })

  test('other files do not match', () => {
    expect(isApproved('C:/p/app/b.py', run, 'C:/p')).toBe(false)
    expect(isApproved('C:/p/src/y.tsx', run, 'C:/p')).toBe(false)
    expect(isApproved('C:/p/lib/src/y.ts', run, 'C:/p')).toBe(false)
  })

  test('a single star stays in one folder', () => {
    const one: Run = { mode: 'strict', root: 'C:/p', changes: [], patterns: [{ glob: 'src/*.ts', command: 'x' }] }
    expect(isApproved('C:/p/src/a.ts', one, 'C:/p')).toBe(true)
    expect(isApproved('C:/p/src/x/a.ts', one, 'C:/p')).toBe(false)
  })

  test('a sibling folder or an escape is outside the project', () => {
    expect(isInside('C:/p/a.py', 'C:/p')).toBe(true)
    expect(isInside('C:/p-old/a.py', 'C:/p')).toBe(false)
    expect(isInside('C:/p/../q/a.py', 'C:/p')).toBe(false)
  })

  test('a POSIX root keeps letter case', () => {
    expect(isApproved('/p/app/a.py', run, '/p')).toBe(true)
    expect(isApproved('/p/app/A.py', run, '/p')).toBe(false)
  })
})

describe('delete commands', () => {
  test('are found at the start of any command', () => {
    for (const command of [
      'rm a', 'cd x && rm -rf y', 'rmdir d', 'del a', 'erase a', 'rd d', 'ri a', 'Remove-Item a',
      'git rm a', 'git clean -fd', 'unlink a', 'find . -delete', 'ls\nrm a', 'sudo rm a',
      'ls | xargs rm', 'find . -name x -exec rm {} +', 'find . -execdir rm {} +',
      'cmd /c del a.py', 'cmd //c "del a.py"', 'npx rimraf dist', 'rimraf dist',
      'powershell -Command "Remove-Item a.py"', 'pwsh -NoProfile -c "ri a"', 'bash -c "rm a.py"', "sh -c 'rm a'",
      'command rm a', '\\rm a', '/bin/rm a', 'env rm a', '{ rm a; }', 'echo `rm a`',
      'gci | % { Remove-Item $_ }', '[IO.File]::Delete("a")', '[System.IO.Directory]::Delete("d")',
      'git checkout -- .', 'git checkout .', 'git restore src', 'git reset --hard HEAD~1', 'git stash -u', 'git stash',
      'git -C x checkout -- a', 'git checkout a.py', 'git checkout HEAD a.py', 'git checkout main src',
      'time rm a', 'sudo -u x rm a', 'sudo -E rm a',
    ]) {
      expect(`${command}: ${isDelete(command)}`).toBe(`${command}: true`)
    }
  })

  test('are not seen inside other words or quoted text', () => {
    for (const command of [
      'npm run format', 'git commit -m "remove rm"', 'ls terraform', 'echo model', 'git checkout -b feat/x',
      'git checkout main', 'git checkout -b feat/x origin/main', 'git checkout -t origin/dev', 'git checkout v1.2.3',
      'git restore --staged a', 'git reset HEAD a', 'git stash list', 'git stash pop',
      'echo ${HOME}', 'npx prettier --write .',
    ]) {
      expect(`${command}: ${isDelete(command)}`).toBe(`${command}: false`)
    }
  })
})
