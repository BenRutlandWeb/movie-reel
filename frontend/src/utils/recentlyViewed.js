const STORAGE_KEY = 'movie-reel_recently_viewed'
const MAX_ITEMS = 10

export function getRecentlyViewed() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function addRecentlyViewed(item) {
  const entry = {
    id: item.id,
    title: item.title,
    year: item.year,
    media_type: item.media_type,
    poster_url: item.poster_url || null,
    viewedAt: Date.now(),
  }

  const existing = getRecentlyViewed().filter((r) => r.id !== item.id)
  const next = [entry, ...existing].slice(0, MAX_ITEMS)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // storage full or unavailable
  }

  return next
}

export function getRecentlyViewedByType(mediaType) {
  return getRecentlyViewed().filter((r) => r.media_type === mediaType)
}
