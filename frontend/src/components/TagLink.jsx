import { Link } from 'react-router-dom'

export default function TagLink({ name, kind }) {
  const className = kind === 'category' ? 'tag-link tag-category' : 'tag-link'
  return (
    <Link to={`/search?tag=${encodeURIComponent(name)}`} className={className}>
      {name}
    </Link>
  )
}
