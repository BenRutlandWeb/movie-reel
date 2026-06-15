const STORAGE_KEY = 'movie-reel_streamer_prefs'

export function getSelectedStreamers() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return null
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function setSelectedStreamers(ids, allProviderIds = null) {
  try {
    const isAllSelected = allProviderIds
      && ids.length === allProviderIds.length
      && allProviderIds.every((id) => ids.includes(id))

    if (isAllSelected) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
    }
    window.dispatchEvent(new CustomEvent('streamer-prefs-changed'))
  } catch {
    // storage full or unavailable
  }
}

export function hasStreamerFilter() {
  const selected = getSelectedStreamers()
  return selected !== null
}

export function isStreamerVisible(providerId) {
  const selected = getSelectedStreamers()
  if (selected === null) return true
  return selected.includes(providerId)
}

export function filterProviders(providers) {
  const selected = getSelectedStreamers()
  if (selected === null) return providers
  return providers.filter((p) => selected.includes(p.provider_id))
}
