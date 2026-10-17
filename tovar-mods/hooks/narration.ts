import type { SessionMessage } from 'claude-code'

import type { Flight, Mood } from '../types'
import type { Character } from './character'

// A character's emoji and color, read from their profile file.
export type Look = { emoji: string; color: string }

// Used when a profile has no color of its own.
export const COLORS: Record<Mood, string> = {
  calm: '#5fb4ff',
  working: '#f8d030',
  burning: '#f07030',
}

// The facts on line 2 until the narration arrives.
export const caption = (now: Flight): string => {
  if (now.mood === 'working') {
    return `${now.tools} tool calls so far`
  }
  if (now.mood === 'burning') {
    return `${now.failures} of ${now.tools} tool calls failed last turn`
  }
  if (now.ran !== null) {
    return `ran ${now.ran}`
  }
  return now.seconds === null
    ? 'waiting for your first prompt'
    : `last turn ${now.seconds}s, ${now.tools} tool calls`
}

export const LINE_RULES = `You voice a fictional character who narrates a coding session.
Rules:
- Follow the character profile: voice, reactions to success and errors, sounds, quotes.
- Say what really happened in the conversation. Never invent results.
- Plain text only: no markdown, no emoji, no surrounding quotes, no name prefix.
- If the profile says the character does not speak: write two lines. First line: only their sounds and noises out loud, never real words. Second line: their thoughts in plain words, in their style, summing up what happened. Shape:\n  Hup! Hyaah!\n  The login bug is fixed and the tests pass.
- A famous quote from the profile is welcome when it fits naturally.`

export const TURN_RULES = `${LINE_RULES}
- 2 to 3 short sentences, at most 300 characters, about the last exchange only.`

export const RECAP_RULES = `${LINE_RULES}
- A recap of the whole session: 3 to 5 short sentences, at most 600 characters.`

export const ASK_RULES = `${LINE_RULES}
- The user must answer the question below. Read the question and every option.
- If one option is recommended, say in character why it is a good pick: 1 to 2 short sentences, at most 220 characters.
- If no option is recommended, never pick one: say one short line, at most 120 characters, that this character would say while someone has to choose.`

// The questions of a question dialog as plain lines, and whether one of the
// options is marked as recommended. Anything malformed is left out.
export const questionsOf = (questions: unknown): { text: string; hasPick: boolean } => {
  if (!Array.isArray(questions)) {
    return { text: '', hasPick: false }
  }
  let hasPick = false
  const blocks = questions.flatMap(q => {
    if (typeof q !== 'object' || q === null) {
      return []
    }
    const { question, options } = q as { question?: unknown; options?: unknown }
    const lines = typeof question === 'string' ? [`Question: ${question}`] : []
    for (const option of Array.isArray(options) ? options : []) {
      const { label, description } = (typeof option === 'object' && option !== null ? option : {}) as {
        label?: unknown
        description?: unknown
      }
      if (typeof label !== 'string') {
        continue
      }
      if (/\(recommended\)/i.test(label)) {
        hasPick = true
      }
      lines.push(`- ${label}${typeof description === 'string' && description !== '' ? `: ${description}` : ''}`)
    }
    return lines.length > 0 ? [lines.join('\n')] : []
  })
  return { text: blocks.join('\n\n'), hasPick }
}

export const slug = (name: string): string =>
  name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

export const clip = (text: string, max: number): string =>
  text.length > max ? `${text.slice(0, max - 1)}…` : text

// Messages as plain lines, keeping the newest `max` characters.
export const transcript = (messages: readonly SessionMessage[], max: number): string => {
  const lines = messages
    .map(m => {
      const tools = m.toolUses.length > 0 ? ` [tools: ${m.toolUses.map(t => t.tool).join(', ')}]` : ''
      const text = m.text.trim()
      return text === '' && tools === '' ? '' : `${m.role === 'user' ? 'User' : 'Assistant'}: ${text}${tools}`
    })
    .filter(line => line !== '')
    .join('\n')
  return lines.length > max ? lines.slice(-max) : lines
}

export const isSilent = (profile: string): boolean => /\*\*Speaks:\*\*\s*NO\b/i.test(profile)

// A silent character's narration keeps two lines: sounds, then thoughts.
// Anyone else's is one paragraph, whatever line breaks the model sent.
export const shape = (text: string, silent: boolean, max: number): string => {
  if (!silent) {
    return tidy(text, max)
  }
  const [sounds = '', ...thoughts] = text.split(/\n+/).map(line => tidy(line, max)).filter(line => line !== '')
  return thoughts.length > 0 ? `${sounds}\n${tidy(thoughts.join(' '), max)}` : sounds
}

// Markdown structure the model sent anyway: heading, list and quote marks at
// a line start, paired stars (1 to 3) or single underscores around words, and
// paired code ticks. A lone star, tick or underscore is a fact (2*3=6,
// footnote*, __init__) and stays.
const unmark = (text: string): string =>
  text
    .replace(/^[ \t]*(#{1,6}|[-+]|\*(?=[ \t])|>)[ \t]+/gm, '')
    .replace(/(?<![\w*])(\*{1,3})(?=[^\s*])([^*\n]*?[^\s*])\1(?![\w*])/g, '$2')
    .replace(/(?<![\w_])_(?=[^\s_])([^_\n]*?[^\s_])_(?![\w_])/g, '$1')
    .replace(/`([^`\n]*)`/g, '$1')

const unquote = (text: string): string => text.trim().replace(/^["“”']+|["“”']+$/g, '')

export const tidy = (text: string, max: number): string =>
  clip(unquote(unmark(unquote(text)).replace(/\s+/g, ' ')), max)

// Used for a character with no thinking actions of their own.
export const THINKING = ['thinking', 'pondering', 'meditating', 'daydreaming']

// What the character does on screen until their narration arrives.
export const thinking = (who: Character, n: number): string => {
  const pool = who.thinks ?? THINKING
  return pool[n % pool.length] ?? 'thinking'
}

export const lookIn = (profile: string, mood: Mood): Look => ({
  emoji: /\*\*Emoji:\*\*\s*(\S+)/.exec(profile)?.[1] ?? '🎮',
  color: /\*\*Color:\*\*\s*(#[0-9a-fA-F]{6})/.exec(profile)?.[1] ?? COLORS[mood],
})
