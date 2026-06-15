import { Link } from 'react-router-dom'

export default function PersonCard({ person, showCharacter }) {
  return (
    <Link to={`/people/${person.id}`} className="person-card">
      <div className="person-avatar">
        {person.profile_url ? (
          <img src={person.profile_url} alt={person.name} loading="lazy" />
        ) : (
          <span>👤</span>
        )}
      </div>
      <div className="person-name">{person.name}</div>
      {showCharacter && person.character_name && (
        <div className="person-role">{person.character_name}</div>
      )}
      {!showCharacter && person.role && (
        <div className="person-role">{person.role}</div>
      )}
    </Link>
  )
}
