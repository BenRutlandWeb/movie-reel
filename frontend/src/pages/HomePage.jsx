import { useEffect, useState } from 'react'

import MediaReel from '../components/MediaReel'

import { fetchMedia, fetchRecentlyAdded, fetchTags } from '../api'

import { getRecentlyViewed, getRecentlyViewedByType } from '../utils/recentlyViewed'

import { getWatchlist } from '../utils/watchlist'

import { getSessionReels } from '../utils/sessionReels'

export default function HomePage() {
  const [loading, setLoading] = useState(true)
  const [watchlist, setWatchlist] = useState([])
  const [recentlyAdded, setRecentlyAdded] = useState([])
  const [recentAll, setRecentAll] = useState([])
  const [recentMovies, setRecentMovies] = useState([])
  const [recentTv, setRecentTv] = useState([])
  const [categoryReels, setCategoryReels] = useState([])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)

      const watchlistItems = getWatchlist()
      const recent = getRecentlyViewed()
      const recentMovieItems = getRecentlyViewedByType('movie')
      const recentTvItems = getRecentlyViewedByType('tv')

      setWatchlist(watchlistItems)
      setRecentAll(recent)
      setRecentMovies(recentMovieItems)
      setRecentTv(recentTvItems)

      try {
        const [tags, added] = await Promise.all([fetchTags(), fetchRecentlyAdded()])
        if (!cancelled) setRecentlyAdded(added)

        const sessionTags = getSessionReels(tags)

        const reelData = await Promise.all(
          sessionTags.map(async (tag) => {
            const items = await fetchMedia({ tag: tag.name, sort: 'title' })
            return {
              title: tag.name,
              kind: tag.kind,
              items: items.slice(0, 20),
              seeAllHref: `/search?tag=${encodeURIComponent(tag.name)}`,
            }
          }),
        )

        if (!cancelled) {
          setCategoryReels(reelData.filter((r) => r.items.length > 0))
        }
      } catch (err) {
        console.error(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const hasContent =
    watchlist.length > 0 ||
    recentlyAdded.length > 0 ||
    recentAll.length > 0 ||
    recentMovies.length > 0 ||
    recentTv.length > 0 ||
    categoryReels.length > 0

  if (loading) {
    return <div className="loading">Loading…</div>
  }

  if (!hasContent) {
    return (
      <div className="empty">
        <h2>Welcome to Movie Reel</h2>
        <p>
          Import your collection from Settings, then browse Movies and TV Shows — your
          watchlist, recently added titles, recently viewed titles, and category reels will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="home">
      <MediaReel title="Watchlist" items={watchlist} />
      <MediaReel title="Recently Added" items={recentlyAdded} />
      <MediaReel title="Recently Viewed" items={recentAll} />
      <MediaReel title="Recently Viewed Movies" items={recentMovies} seeAllHref="/movies" />
      <MediaReel title="Recently Viewed TV Shows" items={recentTv} seeAllHref="/tv" />
      {categoryReels.map((reel) => (
        <MediaReel
          key={`${reel.kind}-${reel.title}`}
          title={reel.title}
          items={reel.items}
          seeAllHref={reel.seeAllHref}
        />
      ))}
    </div>
  )
}
