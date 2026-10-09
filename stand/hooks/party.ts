export const pick = <T>(items: T[], rng: () => number = Math.random): T | undefined =>
  items.length === 0 ? undefined : items[Math.min(items.length - 1, Math.floor(rng() * items.length))]

export const pickName = (
  names: string[],
  used: string[],
  rng: () => number = Math.random,
): string | null => {
  if (names.length === 0) return null
  const free = names.filter(n => !used.includes(n))
  return pick(free.length > 0 ? free : names, rng) ?? null
}
