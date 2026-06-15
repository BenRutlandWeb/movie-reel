const STORAGE_KEY = 'movie-reel_favourites'

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

export function getFavourites() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function isFavourite(id) {
  return getFavourites().some((f) => f.id === id)
}

export function toggleFavourite(item) {
  const entry = toEntry(item)
  const existing = getFavourites()
  const index = existing.findIndex((f) => f.id === item.id)

  let next
  if (index >= 0) {
    next = existing.filter((f) => f.id !== item.id)
  } else {
    next = [entry, ...existing]
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // storage full or unavailable
  }

  return { favourites: next, isFavourite: index < 0 }
}
