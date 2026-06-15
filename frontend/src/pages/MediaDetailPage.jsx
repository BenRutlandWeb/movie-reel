import { useEffect, useState } from 'react'

import { Link, useParams } from 'react-router-dom'

import BbfcRating from '../components/BbfcRating'

import MediaActions from '../components/MediaActions'

import MediaCard from '../components/MediaCard'

import MediaRating from '../components/MediaRating'

import PersonCard from '../components/PersonCard'

import StreamingProviders from '../components/StreamingProviders'

import TagLink from '../components/TagLink'

import SeasonTabs from '../components/SeasonTabs'

import { fetchMediaDetail } from '../api'

import { addRecentlyViewed } from '../utils/recentlyViewed'



export default function MediaDetailPage() {

  const { id } = useParams()

  const [media, setMedia] = useState(null)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState(null)

  const [activeSeason, setActiveSeason] = useState(0)



  useEffect(() => {

    setLoading(true)

    setActiveSeason(0)

    fetchMediaDetail(id)

      .then((data) => {

        setMedia(data)

        addRecentlyViewed(data)

      })

      .catch((e) => setError(e.message))

      .finally(() => setLoading(false))

  }, [id])



  if (loading) return <div className="loading">Loading…</div>

  if (error) return <div className="empty"><h2>{error}</h2></div>

  if (!media) return null



  return (

    <div>

      <Link to="/" className="back-link">← Back</Link>



      <div className="detail-hero">

        {media.backdrop_url && (

          <div

            className="detail-backdrop"

            style={{ backgroundImage: `url(${media.backdrop_url})` }}

          />

        )}

        <div className="detail-content">

          <div className="detail-poster">

            {media.poster_url ? (

              <img src={media.poster_url} alt={media.title} />

            ) : (

              <div className="placeholder" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '3rem' }}>🎬</div>

            )}

          </div>

          <div className="detail-info">

            <h1>{media.title}</h1>

            <div className="detail-meta">

              {media.year && <span>{media.year}</span>}

              <span className={`badge badge-${media.media_type}`}>

                {media.media_type === 'movie' ? 'Movie' : 'TV Show'}

              </span>

              {media.runtime && <span>{media.runtime} min</span>}

              <MediaRating voteAverage={media.vote_average} voteCount={media.vote_count} />

              <BbfcRating rating={media.certification} />

            </div>

            <MediaActions item={media} />

            {(media.genres?.length > 0 || media.tags?.length > 0) && (

              <div className="tag-list">

                {media.genres?.map((g) => (

                  <TagLink key={`g-${g}`} name={g} kind="genre" />

                ))}

                {media.tags?.map((t) => (

                  <TagLink key={`t-${t}`} name={t} kind="category" />

                ))}

              </div>

            )}

            {media.overview && <p className="overview">{media.overview}</p>}

          </div>

        </div>

      </div>



      <StreamingProviders providers={media.streaming_providers || []} />



      {media.media_type === 'tv' && media.season_details?.length > 0 && (

        <div className="section">

          <h2>Episodes</h2>

          <SeasonTabs

            mediaId={media.id}

            seasons={media.season_details}

            activeIndex={activeSeason}

            onSelect={setActiveSeason}

          />

        </div>

      )}



      {media.media_type === 'tv' && media.seasons?.length > 0 && !media.season_details?.length && (

        <div className="section">

          <h2>Owned seasons</h2>

          <div className="tag-list">

            {media.seasons.map((season) => (

              <span key={season} className="genre-tag">

                {season === 'specials' ? 'Specials' : `Season ${season}`}

              </span>

            ))}

          </div>

        </div>

      )}



      {media.crew?.length > 0 && (

        <div className="section">

          <h2>Director & Crew</h2>

          <div className="people-row">

            {media.crew.map((person) => (

              <PersonCard key={`${person.id}-${person.role}`} person={person} />

            ))}

          </div>

        </div>

      )}



      {media.cast?.length > 0 && (

        <div className="section">

          <h2>Cast</h2>

          <div className="people-row">

            {media.cast.map((person) => (

              <PersonCard key={person.id} person={person} showCharacter />

            ))}

          </div>

        </div>

      )}



      {media.related?.length > 0 && (

        <div className="section">

          <h2>Related</h2>

          <div className="grid">

            {media.related.map((item) => (

              <MediaCard key={item.id} item={item} />

            ))}

          </div>

        </div>

      )}

    </div>

  )

}

