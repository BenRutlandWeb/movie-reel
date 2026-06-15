import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSearchSuggestions } from '../api'

function suggestionKey(item) {
  if (item.type === 'media') return `media-${item.id}`
  if (item.type === 'person') return `person-${item.id}`
  return `tag-${item.kind}-${item.name}`
}

function SuggestionThumb({ item }) {
  if (item.type === 'person') {
    return (
      <span className="search-suggestion-poster search-suggestion-profile">
        {item.profile_url ? (
          <img src={item.profile_url} alt="" />
        ) : (
          <span className="search-suggestion-placeholder">👤</span>
        )}
      </span>
    )
  }

  if (item.type === 'tag') {
    return (
      <span className="search-suggestion-poster search-suggestion-label">
        <span className="search-suggestion-placeholder">{item.kind === 'genre' ? '🎭' : '🏷️'}</span>
      </span>
    )
  }

  return (
    <span className="search-suggestion-poster">
      {item.poster_url ? (
        <img src={item.poster_url} alt="" />
      ) : (
        <span className="search-suggestion-placeholder">🎬</span>
      )}
    </span>
  )
}

function SuggestionBody({ item }) {
  if (item.type === 'person') {
    return (
      <span className="search-suggestion-body">
        <span className="search-suggestion-title">{item.name}</span>
        <span className="search-suggestion-meta">
          <span className="search-suggestion-hint">Cast</span>
          {item.known_for_department && <span>{item.known_for_department}</span>}
        </span>
      </span>
    )
  }

  if (item.type === 'tag') {
    return (
      <span className="search-suggestion-body">
        <span className="search-suggestion-title">{item.name}</span>
        <span className="search-suggestion-meta">
          <span className="search-suggestion-hint">
            {item.kind === 'genre' ? 'Genre' : 'Tag'}
          </span>
          {item.count > 0 && <span>{item.count} titles</span>}
        </span>
      </span>
    )
  }

  return (
    <span className="search-suggestion-body">
      <span className="search-suggestion-title">{item.title}</span>
      <span className="search-suggestion-meta">
        {item.year && <span>{item.year}</span>}
        <span className={`badge badge-${item.media_type}`}>
          {item.media_type === 'movie' ? 'Movie' : 'TV'}
        </span>
      </span>
    </span>
  )
}

export default function HeaderSearch({ className, query, onChange, onSubmit }) {
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSuggestions([])
      setOpen(false)
      return undefined
    }

    const timer = setTimeout(() => {
      fetchSearchSuggestions(trimmed, 3)
        .then((results) => {
          setSuggestions(results)
          setOpen(results.length > 0)
        })
        .catch(() => {
          setSuggestions([])
          setOpen(false)
        })
    }, 200)

    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    function handlePointerDown(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [])

  function goToResult(item) {
    setOpen(false)
    if (item.type === 'person') {
      navigate(`/people/${item.id}`)
      return
    }
    if (item.type === 'tag') {
      navigate(`/search?tag=${encodeURIComponent(item.name)}`)
      return
    }
    navigate(`/media/${item.id}`)
  }

  function handleSubmit(e) {
    setOpen(false)
    onSubmit(e)
  }

  const showSuggestions = open && suggestions.length > 0

  return (
    <form className={className} onSubmit={handleSubmit}>
      <div className="header-search-wrap" ref={wrapRef}>
        <input
          type="search"
          className="search-input"
          placeholder="Search titles, cast, genres…"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setOpen(true)
          }}
          aria-label="Search"
          aria-expanded={showSuggestions}
          aria-autocomplete="list"
          aria-controls={showSuggestions ? 'header-search-suggestions' : undefined}
          autoComplete="off"
        />
        {showSuggestions && (
          <ul
            id="header-search-suggestions"
            className="search-suggestions"
            role="listbox"
            aria-label="Search suggestions"
          >
            {suggestions.map((item) => (
              <li key={suggestionKey(item)} role="option">
                <button type="button" className="search-suggestion" onClick={() => goToResult(item)}>
                  <SuggestionThumb item={item} />
                  <SuggestionBody item={item} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </form>
  )
}
