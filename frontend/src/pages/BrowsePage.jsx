import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import MediaCard from '../components/MediaCard'
import { fetchMedia, fetchTags } from '../api'
import { getSelectedStreamers, hasStreamerFilter } from '../utils/streamerPrefs'

export default function BrowsePage({ defaultType = '', title = 'Browse' }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [media, setMedia] = useState([])
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [myStreamersOnly, setMyStreamersOnly] = useState(false)
  const [streamerFilterAvailable, setStreamerFilterAvailable] = useState(hasStreamerFilter())

  const mediaType = searchParams.get('type') || defaultType
  const tag = searchParams.get('tag') || ''
  const q = searchParams.get('q') || ''
  const sort = searchParams.get('sort') || 'title'

  useEffect(() => {
    fetchTags().then(setTags).catch(console.error)
  }, [])

  useEffect(() => {
    function onPrefsChanged() {
      setStreamerFilterAvailable(hasStreamerFilter())
    }
    window.addEventListener('streamer-prefs-changed', onPrefsChanged)
    return () => window.removeEventListener('streamer-prefs-changed', onPrefsChanged)
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = { sort: q ? 'relevance' : sort }
    if (mediaType) params.media_type = mediaType
    if (tag) params.tag = tag
    if (q) params.q = q
    if (myStreamersOnly) {
      const selected = getSelectedStreamers()
      if (selected !== null && selected.length === 0) {
        setMedia([])
        setLoading(false)
        return undefined
      }
      if (selected?.length) {
        params.providers = selected.join(',')
      }
    }
    fetchMedia(params)
      .then(setMedia)
      .catch(console.error)
      .finally(() => setLoading(false))
    return undefined
  }, [mediaType, tag, q, sort, myStreamersOnly])

  function updateParam(key, value) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next)
  }

  return (
    <div>
      <h1 className="page-title">{title}</h1>

      <div className="toolbar">
        {!defaultType && (
          <select value={mediaType} onChange={(e) => updateParam('type', e.target.value)}>
            <option value="">All media</option>
            <option value="movie">Movies</option>
            <option value="tv">TV Shows</option>
          </select>
        )}
        <select value={tag} onChange={(e) => updateParam('tag', e.target.value)}>
          <option value="">All tags</option>
          {tags.map((t) => (
            <option key={`${t.kind}-${t.name}`} value={t.name}>
              {t.name} ({t.count})
            </option>
          ))}
        </select>
        <select value={sort} onChange={(e) => updateParam('sort', e.target.value)}>
          <option value="title">Title A–Z</option>
          <option value="year">Year (newest)</option>
          <option value="updated">Recently updated</option>
        </select>
        {streamerFilterAvailable && (
          <button
            type="button"
            className={`media-action-btn${myStreamersOnly ? ' active' : ''}`}
            onClick={() => setMyStreamersOnly((v) => !v)}
            aria-pressed={myStreamersOnly}
          >
            {myStreamersOnly ? 'My streamers on' : 'My streamers only'}
          </button>
        )}
      </div>

      {myStreamersOnly && (
        <div className="active-filter">
          Showing titles on your selected streaming services
          <button type="button" onClick={() => setMyStreamersOnly(false)}>Clear</button>
        </div>
      )}

      {tag && (
        <div className="active-filter">
          Filtered by tag: <strong>{tag}</strong>
          <button type="button" onClick={() => updateParam('tag', '')}>Clear</button>
        </div>
      )}

      {q && (
        <div className="active-filter">
          Search: <strong>{q}</strong>
          <button type="button" onClick={() => updateParam('q', '')}>Clear</button>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading…</div>
      ) : media.length === 0 ? (
        <div className="empty">
          <h2>{q || tag ? 'No matches found' : 'Nothing here yet'}</h2>
          <p>
            {q || tag
              ? 'Try a different search term or tag.'
              : 'Import your collection from Settings to get started.'}
          </p>
        </div>
      ) : (
        <div className="grid">
          {media.map((item) => (
            <MediaCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
