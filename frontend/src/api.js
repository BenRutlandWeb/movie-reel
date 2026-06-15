const API = '/api'

export const RECENT_ADDED_DAYS = 30

export async function fetchSearchSuggestions(query, limit = 3) {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  const res = await fetch(`${API}/media/suggest?${params}`)
  if (!res.ok) throw new Error('Failed to fetch search suggestions')
  return res.json()
}

export async function fetchMedia(params = {}) {
  const query = new URLSearchParams(params).toString()
  const res = await fetch(`${API}/media?${query}`)
  if (!res.ok) throw new Error('Failed to fetch media')
  return res.json()
}

export async function fetchMediaDetail(id) {
  const res = await fetch(`${API}/media/${id}`)
  if (!res.ok) throw new Error('Media not found')
  return res.json()
}

export async function fetchEpisode(mediaId, season, episode) {
  const res = await fetch(`${API}/media/${mediaId}/seasons/${season}/episodes/${episode}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Episode not found')
  }
  return res.json()
}

export async function fetchPerson(id) {
  const res = await fetch(`${API}/people/${id}`)
  if (!res.ok) throw new Error('Person not found')
  return res.json()
}

export async function fetchGenres() {
  const res = await fetch(`${API}/media/genres`)
  if (!res.ok) throw new Error('Failed to fetch genres')
  return res.json()
}

export async function fetchTags() {
  const res = await fetch(`${API}/media/tags`)
  if (!res.ok) throw new Error('Failed to fetch tags')
  return res.json()
}

export async function fetchProviders() {
  const res = await fetch(`${API}/media/providers`)
  if (!res.ok) throw new Error('Failed to fetch providers')
  return res.json()
}

export async function exportCollection() {
  const res = await fetch(`${API}/media/export/all`)
  if (!res.ok) throw new Error('Export failed')
  return res.json()
}

export async function importStubs(items, fetchMetadata = true) {
  const res = await fetch(`${API}/media/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, fetch_metadata: fetchMetadata }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Import failed')
  }
  return res.json()
}

export async function fetchImportStatus() {
  const res = await fetch(`${API}/media/jobs/status`)
  if (!res.ok) throw new Error('Failed to fetch job status')
  return res.json()
}

export async function fetchJobsStatus() {
  return fetchImportStatus()
}

export async function fetchMetadataErrors() {
  const res = await fetch(`${API}/media/errors`)
  if (!res.ok) throw new Error('Failed to fetch metadata errors')
  return res.json()
}

export async function retryMetadata(mediaId) {
  const res = await fetch(`${API}/media/${mediaId}/retry`, { method: 'POST' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Retry failed')
  }
  return res.json()
}

export async function resolveMetadataError(mediaId, { notes, tmdbId } = {}) {
  const res = await fetch(`${API}/media/${mediaId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes: notes || null, tmdb_id: tmdbId || null }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Resolve failed')
  }
  return res.json()
}

export async function refreshMetadata() {
  const res = await fetch(`${API}/media/refresh-metadata`, { method: 'POST' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to start metadata rescan')
  }
  return res.json()
}

export async function searchTmdb(query, mediaType, year) {
  const params = new URLSearchParams({ q: query })
  if (mediaType) params.set('media_type', mediaType)
  if (year) params.set('year', String(year))
  const res = await fetch(`${API}/tmdb/search?${params}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Search failed')
  }
  return res.json()
}

export async function fetchRecentlyAdded(days = RECENT_ADDED_DAYS) {
  const res = await fetch(`${API}/media/recent?days=${days}`)
  if (!res.ok) throw new Error('Failed to fetch recently added titles')
  return res.json()
}

export async function deleteMedia(id) {
  const res = await fetch(`${API}/media/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to remove title')
  }
  return res.json()
}

export async function addMedia({ tmdbId, mediaType, seasons, tags }) {
  const res = await fetch(`${API}/media/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tmdb_id: tmdbId,
      media_type: mediaType,
      seasons: seasons || [],
      tags: tags || [],
    }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to add title')
  }
  return res.json()
}

export async function refreshProviders() {
  const res = await fetch(`${API}/media/refresh-providers`, { method: 'POST' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to refresh streaming services')
  }
  return res.json()
}
