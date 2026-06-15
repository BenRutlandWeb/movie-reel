import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import MediaRating from '../components/MediaRating'
import TagLink from '../components/TagLink'
import { fetchEpisode } from '../api'

function formatRuntime(minutes) {
  if (!minutes) return null
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

function seasonLabel(season) {
  return season === 'specials' ? 'Specials' : `Season ${season}`
}

export default function EpisodePage() {
  const { id, season, episode } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchEpisode(id, season, episode)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id, season, episode])

  if (loading) return <div className="loading">Loading…</div>
  if (error) return <div className="empty"><h2>{error}</h2></div>
  if (!data) return null

  const showHref = `/media/${data.media_id}`

  return (
    <div>
      <Link to={showHref} className="back-link">← Back to {data.show_title}</Link>

      <div className="episode-hero">
        {data.still_url && (
          <div
            className="episode-backdrop"
            style={{ backgroundImage: `url(${data.still_url})` }}
          />
        )}
        <div className="episode-hero-content">
          <div className="episode-breadcrumb">
            <Link to={showHref}>{data.show_title}</Link>
            <span className="episode-breadcrumb-sep">›</span>
            <span>{seasonLabel(data.season_number)}</span>
          </div>
          <h1 className="episode-title">
            <span className="episode-title-number">E{data.episode_number}</span>
            {data.name}
          </h1>
          <div className="detail-meta">
            {data.air_date && <span>{data.air_date}</span>}
            {data.runtime && <span>{formatRuntime(data.runtime)}</span>}
            <MediaRating voteAverage={data.vote_average} voteCount={data.vote_count} />
          </div>
          {(data.genres?.length > 0 || data.tags?.length > 0) && (
            <div className="tag-list">
              {data.genres?.map((g) => (
                <TagLink key={`g-${g}`} name={g} kind="genre" />
              ))}
              {data.tags?.map((t) => (
                <TagLink key={`t-${t}`} name={t} kind="category" />
              ))}
            </div>
          )}
          {data.overview && <p className="overview">{data.overview}</p>}
        </div>
      </div>

      {data.crew?.length > 0 && (
        <div className="section">
          <h2>Crew</h2>
          <div className="episode-crew-list">
            {data.crew.map((person) => (
              <div key={`${person.name}-${person.job}`} className="episode-crew-item">
                <span className="episode-crew-name">{person.name}</span>
                <span className="episode-crew-job">{person.job}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.guest_stars?.length > 0 && (
        <div className="section">
          <h2>Guest Stars</h2>
          <div className="people-row">
            {data.guest_stars.map((person) => (
              <div key={person.id} className="person-card">
                <div className="person-avatar">
                  {person.profile_url ? (
                    <img src={person.profile_url} alt={person.name} loading="lazy" />
                  ) : (
                    <div className="placeholder">👤</div>
                  )}
                </div>
                <div className="person-name">{person.name}</div>
                {person.character_name && (
                  <div className="person-character">{person.character_name}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
