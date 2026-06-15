import { Link } from 'react-router-dom'
import MediaRating from './MediaRating'

function formatRuntime(minutes) {
  if (!minutes) return null
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

function seasonTabLabel(season) {
  if (season.season_number === 'specials') return 'Specials'
  return `Season ${season.season_number}`
}

export default function SeasonTabs({ mediaId, seasons, activeIndex, onSelect }) {
  const active = seasons[activeIndex]

  return (
    <div className="season-tabs">
      <div className="season-tab-list" role="tablist" aria-label="Seasons">
        {seasons.map((season, index) => (
          <button
            key={season.season_number}
            type="button"
            role="tab"
            id={`season-tab-${season.season_number}`}
            aria-selected={index === activeIndex}
            aria-controls={`season-panel-${season.season_number}`}
            className={`season-tab${index === activeIndex ? ' active' : ''}`}
            onClick={() => onSelect(index)}
          >
            {seasonTabLabel(season)}
          </button>
        ))}
      </div>

      {active && (
        <div
          className="season-tab-panel"
          role="tabpanel"
          id={`season-panel-${active.season_number}`}
          aria-labelledby={`season-tab-${active.season_number}`}
        >
          {active.name && active.name !== `Season ${active.season_number}` && (
            <p className="season-panel-title">{active.name}</p>
          )}
          <div className="episode-list">
            {active.episodes.map((ep) => (
              <Link
                key={ep.episode_number}
                to={`/media/${mediaId}/season/${active.season_number}/episode/${ep.episode_number}`}
                className="episode-row episode-row-link"
              >
                {ep.still_url && (
                  <img src={ep.still_url} alt="" className="episode-still" loading="lazy" />
                )}
                <div className="episode-info">
                  <div className="episode-heading">
                    <span className="episode-number">E{ep.episode_number}</span>
                    <span className="episode-name">{ep.name}</span>
                    {ep.runtime && (
                      <span className="episode-runtime">{formatRuntime(ep.runtime)}</span>
                    )}
                    {ep.vote_average != null && (
                      <MediaRating voteAverage={ep.vote_average} voteCount={ep.vote_count} />
                    )}
                  </div>
                  {ep.air_date && <div className="episode-date">{ep.air_date}</div>}
                  {ep.overview && <p className="episode-overview">{ep.overview}</p>}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
