import icon12 from '../assets/bbfc/12.svg?url'
import icon12a from '../assets/bbfc/12a.svg?url'
import icon15 from '../assets/bbfc/15.svg?url'
import iconEighteen from '../assets/bbfc/eighteen.svg?url'
import iconPg from '../assets/bbfc/pg.svg?url'
import iconR18 from '../assets/bbfc/r18.svg?url'
import iconU from '../assets/bbfc/u.svg?url'

const RATING_LABELS = {
  U: 'Universal',
  PG: 'Parental Guidance',
  '12': 'Suitable for 12 years and over',
  '12A': 'Suitable for 12 years and over (cinema)',
  '15': 'Suitable for 15 years and over',
  '18': 'Suitable for adults only',
  R18: 'Restricted to licensed premises',
}

const RATING_ICONS = {
  U: iconU,
  PG: iconPg,
  '12': icon12,
  '12A': icon12a,
  '15': icon15,
  '18': iconEighteen,
  R18: iconR18,
}

function normalizeRating(rating) {
  const value = String(rating).trim().toUpperCase()
  if (RATING_ICONS[value]) return value
  if (value === 'R-18') return 'R18'
  return null
}

export default function BbfcRating({ rating }) {
  if (!rating) return null

  const key = normalizeRating(rating)
  if (!key) return null

  const label = RATING_LABELS[key] || `Rated ${rating}`

  return (
    <span className="bbfc-rating" title={`BBFC ${rating} — ${label}`} aria-label={`BBFC rating ${rating}`}>
      <img src={RATING_ICONS[key]} alt="" className="bbfc-rating-img" />
    </span>
  )
}
