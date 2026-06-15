const SESSION_KEY = 'movie-reel_session_reels'
const REEL_COUNT = 6
const MIN_TAG_COUNT = 2

function shuffle(array) {
  const copy = [...array]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export function getSessionReels(tags) {
  try {
    const stored = sessionStorage.getItem(SESSION_KEY)
    if (stored) return JSON.parse(stored)
  } catch {
    // ignore
  }

  const eligible = tags.filter((t) => t.count >= MIN_TAG_COUNT)
  const picked = shuffle(eligible).slice(0, Math.min(REEL_COUNT, eligible.length))

  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(picked))
  } catch {
    // ignore
  }

  return picked
}
