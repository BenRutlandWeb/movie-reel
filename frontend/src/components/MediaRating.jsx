export default function MediaRating({ voteAverage, voteCount }) {
  if (voteAverage == null) return null

  const score = Math.round(voteAverage * 10) / 10

  return (
    <span className="media-rating" title={voteCount ? `${voteCount.toLocaleString()} votes` : undefined}>
      <span className="media-rating-star" aria-hidden="true">★</span>
      <span className="media-rating-value">{score}</span>
      <span className="media-rating-scale">/10</span>
    </span>
  )
}
