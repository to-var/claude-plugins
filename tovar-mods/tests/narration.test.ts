import { describe, expect, test } from 'claude-code/testing'

import { caption, lookIn, questionsOf, shape, slug, tidy, transcript } from '../hooks/narration'
import { START } from '../hooks/flight'

describe('narration text', () => {
  test('tidy drops markdown and wrapping quotes but keeps snake_case words', () => {
    expect(tidy('"# **Done!** The `user_id` check\n> passes."', 300)).toBe('Done! The user_id check passes.')
    expect(tidy('_quietly_ fixed', 300)).toBe('quietly fixed')
    expect(tidy('“**Wahoo!** The `login` bug\n- is _fixed_, and *all* tests pass.”', 300))
      .toBe('Wahoo! The login bug is fixed, and all tests pass.')
  })

  test('tidy keeps lone stars, ticks and underscores, which are facts', () => {
    for (const fact of ['2*3=6', '5 * 3 is 15', 'a ** b', 'footnote*', '2*3*4', '__init__ ran', 'a ` b', 'snake_case_name']) {
      expect(tidy(fact, 300)).toBe(fact)
    }
  })

  test('tidy drops paired emphasis and a list mark around sounds', () => {
    expect(tidy('*pop* *ding*', 300)).toBe('pop ding')
    expect(tidy('- *Hup!*', 300)).toBe('Hup!')
    expect(tidy('* ***Boom!***', 300)).toBe('Boom!')
  })

  test('tidy clips long text to the limit with an ellipsis', () => {
    const out = tidy('x'.repeat(500), 360)
    expect(out.length).toBe(360)
    expect(out.endsWith('…')).toBe(true)
  })

  test('a silent shape keeps sounds on the first line and thoughts on the second', () => {
    expect(shape('- *Hup!*\n\nIt works.\nAll green.', true, 300)).toBe('Hup!\nIt works. All green.')
    expect(shape('Hup!', true, 300)).toBe('Hup!')
  })

  test('the caption never shows undefined for any mood', () => {
    for (const mood of ['calm', 'working', 'burning'] as const) {
      expect(caption({ ...START('b'), mood })).not.toMatch(/undefined|null|NaN/)
    }
  })

  test('a profile without emoji or color uses the defaults', () => {
    expect(lookIn('# Nobody', 'burning')).toEqual({ emoji: '🎮', color: '#f07030' })
  })

  test('slug matches the profile file names', () => {
    expect(slug('Mr. Game & Watch')).toBe('mr-game-watch')
    expect(slug('R.O.B.')).toBe('r-o-b')
  })

  test('the transcript keeps the newest text and names the tools', () => {
    const lines = transcript([
      { role: 'user', text: 'old '.repeat(50), toolUses: [] },
      { role: 'assistant', text: 'new', toolUses: [{ tool: 'Bash' }] },
    ] as never, 40)
    expect(lines.length).toBe(40)
    expect(lines.endsWith('Assistant: new [tools: Bash]')).toBe(true)
  })

  test('a question reads as plain lines and spots the recommended option', () => {
    const read = questionsOf([
      {
        question: 'Which bar?',
        header: 'Bar',
        multiSelect: false,
        options: [
          { label: 'Smash (Recommended)', description: 'The default.' },
          { label: 'Birds', description: 'Three legends.' },
        ],
      },
    ])
    expect(read.hasPick).toBe(true)
    expect(read.text).toContain('Question: Which bar?')
    expect(read.text).toContain('- Smash (Recommended): The default.')
    expect(read.text).toContain('- Birds: Three legends.')
  })

  test('a question with no recommended option, or a broken input, has no pick', () => {
    expect(questionsOf([{ question: 'A or B?', options: [{ label: 'A' }, { label: 'B' }] }]).hasPick).toBe(false)
    expect(questionsOf(undefined)).toEqual({ text: '', hasPick: false })
    expect(questionsOf([42, { options: 'x' }]).text).not.toMatch(/undefined/)
  })
})
