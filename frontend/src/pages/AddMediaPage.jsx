import { useCallback, useEffect, useState } from 'react'
import { addMedia, deleteMedia, fetchRecentlyAdded, RECENT_ADDED_DAYS, searchTmdb } from '../api'
import MediaReel from '../components/MediaReel'

const TYPE_LABELS = { movie: 'Movie', tv: 'TV Show' }

export default function AddMediaPage() {
  const [query, setQuery] = useState('')
  const [mediaType, setMediaType] = useState('')
  const [year, setYear] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [addingId, setAddingId] = useState(null)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)
  const [recentlyAdded, setRecentlyAdded] = useState([])
  const [deletingId, setDeletingId] = useState(null)

  const loadRecentlyAdded = useCallback(async () => {
    try {
      const items = await fetchRecentlyAdded()
      setRecentlyAdded(items)
    } catch (err) {
      console.error(err)
    }
  }, [])

  useEffect(() => {
    loadRecentlyAdded()
  }, [loadRecentlyAdded])

  async function handleSearch(e) {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return

    setLoading(true)
    setError(null)
    setSearched(true)
    try {
      const data = await searchTmdb(trimmed, mediaType || undefined, year ? Number(year) : undefined)
      setResults(data)
    } catch (err) {
      setError(err.message)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(item) {
    setAddingId(item.tmdb_id)
    setError(null)
    try {
      await addMedia({
        tmdbId: item.tmdb_id,
        mediaType: item.media_type,
      })
      await loadRecentlyAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setAddingId(null)
    }
  }

  async function handleDelete(item) {
    if (!window.confirm(`Remove "${item.title}" from your collection?`)) return

    setDeletingId(item.id)
    setError(null)
    try {
      await deleteMedia(item.id)
      setRecentlyAdded((prev) => prev.filter((r) => r.id !== item.id))
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="add-media-page">
      <div className="add-media-content">
        <h1 className="page-title">Add to collection</h1>
        <p className="overview" style={{ marginBottom: '1.5rem' }}>
          Search TMDB to add a movie or TV show you own to your collection.
        </p>

        <form className="add-media-form" onSubmit={handleSearch}>
        <input
          type="search"
          className="search-input"
          placeholder="Search TMDB…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <div className="add-media-filters">
          <select
            value={mediaType}
            onChange={(e) => setMediaType(e.target.value)}
            aria-label="Media type"
          >
            <option value="">All types</option>
            <option value="movie">Movies</option>
            <option value="tv">TV shows</option>
          </select>
          <input
            type="number"
            placeholder="Year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            min="1900"
            max="2100"
            aria-label="Year"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            style={{
              background: 'var(--accent)',
              color: 'var(--bg)',
              padding: '0.6rem 1.2rem',
              borderRadius: 'var(--radius)',
              fontWeight: 600,
            }}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {error && <p className="add-media-error">{error}</p>}

      {searched && !loading && results.length === 0 && !error && (
        <p className="overview">No results found. Try a different search.</p>
      )}

      <div className="add-media-results">
        {results.map((item) => (
          <div key={`${item.media_type}-${item.tmdb_id}`} className="add-media-result">
            <div className="add-media-result__poster">
              {item.poster_url ? (
                <img src={item.poster_url} alt="" />
              ) : (
                <div className="add-media-result__poster--empty">?</div>
              )}
            </div>
            <div className="add-media-result__info">
              <h3>
                {item.title}
                {item.year ? ` (${item.year})` : ''}
              </h3>
              <span className={`badge badge--${item.media_type}`}>
                {TYPE_LABELS[item.media_type]}
              </span>
              {item.overview && (
                <p className="overview add-media-result__overview">{item.overview}</p>
              )}
              <button
                type="button"
                onClick={() => handleAdd(item)}
                disabled={addingId === item.tmdb_id}
                className="add-media-result__btn"
              >
                {addingId === item.tmdb_id ? 'Adding…' : 'Add to collection'}
              </button>
            </div>
          </div>
        ))}
      </div>
      </div>

      <MediaReel
        title="Recently Added"
        subtitle={`Added in the last ${RECENT_ADDED_DAYS} days`}
        items={recentlyAdded}
        onDelete={handleDelete}
        deletingId={deletingId}
      />
    </div>
  )
}
