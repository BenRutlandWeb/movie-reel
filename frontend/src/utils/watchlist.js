const STORAGE_KEY = 'movie-reel_watchlist'

function toEntry(item) {
  return {
    id: item.id,
    title: item.title,
    year: item.year,
    media_type: item.media_type,
    poster_url: item.poster_url || null,
    addedAt: Date.now(),
  }
}

export function getWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function isOnWatchlist(id) {
  return getWatchlist().some((w) => w.id === id)
}

export function toggleWatchlist(item) {
  const entry = toEntry(item)
  const existing = getWatchlist()
  const index = existing.findIndex((w) => w.id === item.id)

  let next
  if (index >= 0) {
    next = existing.filter((w) => w.id !== item.id)
  } else {
    next = [entry, ...existing]
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // storage full or unavailable
  }

  return { watchlist: next, isOnWatchlist: index < 0 }
}
