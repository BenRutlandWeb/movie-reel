import { Link, useNavigate } from 'react-router-dom'

export default function MediaCard({ item, compact = false }) {
  const navigate = useNavigate()
  const topTags = [
    ...(item.genres || []).slice(0, 2).map((name) => ({ name, kind: 'genre' })),
    ...(item.tags || []).slice(0, 1).map((name) => ({ name, kind: 'category' })),
  ]

  function goToTag(e, name) {
    e.preventDefault()
    e.stopPropagation()
    navigate(`/search?tag=${encodeURIComponent(name)}`)
  }

  return (
    <Link to={`/media/${item.id}`} className={`card${compact ? ' card-compact' : ''}`}>
      <div className="card-poster">
        {item.poster_url ? (
          <img src={item.poster_url} alt={item.title} loading="lazy" />
        ) : (
          <div className="placeholder">🎬</div>
        )}
      </div>
      <div className="card-body">
        <div className="card-title">{item.title}</div>
        <div className="card-meta">
          {item.year && <span>{item.year}</span>}
          <span className={`badge badge-${item.media_type}`}>
            {item.media_type === 'movie' ? 'Movie' : 'TV'}
          </span>
        </div>
        {topTags.length > 0 && (
          <div className="card-tags">
            {topTags.map((t) => (
              <button
                key={`${t.kind}-${t.name}`}
                type="button"
                className={t.kind === 'category' ? 'tag-link tag-category' : 'tag-link'}
                onClick={(e) => goToTag(e, t.name)}
              >
                {t.name}
              </button>
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
