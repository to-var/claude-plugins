import type { ThemeData } from '../types'

const isTexts = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === 'string')

export const parseTheme = (stdout: string): ThemeData | null => {
  try {
    const out = JSON.parse(stdout)
    const d = out?.data
    if (out?.ok !== true || typeof d?.name !== 'string') return null
    if (!isTexts(d.verbs) || !isTexts(d.announcements) || !isTexts(d.names)) return null
    return {
      name: d.name,
      label: typeof d.label === 'string' ? d.label : '',
      verbs: d.verbs,
      announcements: d.announcements,
      names: d.names,
    }
  } catch {
    return null
  }
}
