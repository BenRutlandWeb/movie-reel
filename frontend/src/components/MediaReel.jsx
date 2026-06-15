import { Link } from 'react-router-dom'
import MediaCard from './MediaCard'

export default function MediaReel({
  title,
  items,
  seeAllHref,
  subtitle,
  onDelete,
  deletingId,
}) {
  if (!items?.length) return null

  return (
    <section className="reel">
      <div className="reel-header">
        <div>
          <h2 className="reel-title">{title}</h2>
          {subtitle && <p className="reel-subtitle">{subtitle}</p>}
        </div>
        {seeAllHref && (
          <Link to={seeAllHref} className="reel-see-all">
            See all
          </Link>
        )}
      </div>
      <div className="reel-row">
        {items.map((item) => (
          <div key={item.id} className="reel-item">
            {onDelete && (
              <button
                type="button"
                className="reel-delete"
                aria-label={`Remove ${item.title}`}
                title="Remove from collection"
                disabled={deletingId === item.id}
                onClick={() => onDelete(item)}
              >
                {deletingId === item.id ? '…' : '×'}
              </button>
            )}
            <MediaCard item={item} compact />
          </div>
        ))}
      </div>
    </section>
  )
}
