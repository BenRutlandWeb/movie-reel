import { useState } from 'react'
import { isFavourite, toggleFavourite } from '../utils/favourites'
import { isOnWatchlist, toggleWatchlist } from '../utils/watchlist'

export default function MediaActions({ item, onChange }) {
  const [fav, setFav] = useState(() => isFavourite(item.id))
  const [watching, setWatching] = useState(() => isOnWatchlist(item.id))

  function handleFavourite() {
    const result = toggleFavourite(item)
    setFav(result.isFavourite)
    onChange?.('favourite', result)
  }

  function handleWatchlist() {
    const result = toggleWatchlist(item)
    setWatching(result.isOnWatchlist)
    onChange?.('watchlist', result)
  }

  return (
    <div className="media-actions-wrap">
      <div className="media-actions">
        <button
          type="button"
          className={`media-action-btn${fav ? ' active' : ''}`}
          onClick={handleFavourite}
          aria-pressed={fav}
        >
          <span className="media-action-icon" aria-hidden="true">{fav ? '♥' : '♡'}</span>
          {fav ? 'Favourited' : 'Favourite'}
        </button>
        <button
          type="button"
          className={`media-action-btn${watching ? ' active' : ''}`}
          onClick={handleWatchlist}
          aria-pressed={watching}
        >
          <span className="media-action-icon" aria-hidden="true">+</span>
          {watching ? 'On Watchlist' : 'Add to Watchlist'}
        </button>
      </div>
    </div>
  )
}
