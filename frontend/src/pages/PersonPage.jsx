import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import MediaCard from '../components/MediaCard'
import { fetchPerson } from '../api'

function calculateAge(birthday, asOf = new Date()) {
  const birth = new Date(birthday)
  if (Number.isNaN(birth.getTime())) return null

  let age = asOf.getFullYear() - birth.getFullYear()
  const monthDiff = asOf.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && asOf.getDate() < birth.getDate())) {
    age -= 1
  }
  return age
}

function formatLifeDates(birthday, deathday) {
  if (!birthday) return null
  const born = new Date(birthday).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  if (!deathday) {
    const age = calculateAge(birthday)
    return age != null ? `Born ${born} (${age} years old)` : `Born ${born}`
  }
  const died = new Date(deathday).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const ageAtDeath = calculateAge(birthday, new Date(deathday))
  return ageAtDeath != null
    ? `${born} – ${died} (${ageAtDeath} years old)`
    : `${born} – ${died}`
}

export default function PersonPage() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPerson(id)
      .then(setPerson)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="loading">Loading…</div>
  if (!person) return <div className="empty"><h2>Person not found</h2></div>

  const lifeDates = formatLifeDates(person.birthday, person.deathday)

  return (
    <div>
      <Link to="/" className="back-link">← Back</Link>

      <div className="person-header">
        <div className="person-avatar person-avatar-lg">
          {person.profile_url ? (
            <img src={person.profile_url} alt={person.name} />
          ) : (
            <span>👤</span>
          )}
        </div>
        <div className="person-header-info">
          <h1>{person.name}</h1>
          {person.known_for_department && (
            <p className="person-department">{person.known_for_department}</p>
          )}
          {lifeDates && <p className="person-dates">{lifeDates}</p>}
          {person.place_of_birth && (
            <p className="person-birthplace">{person.place_of_birth}</p>
          )}
        </div>
      </div>

      {person.biography && (
        <div className="section">
          <h2>Biography</h2>
          <p className="person-biography">{person.biography}</p>
        </div>
      )}

      <div className="section">
        <h2>In your collection</h2>
        {person.media.length === 0 ? (
          <p className="empty-inline">No titles in your collection.</p>
        ) : (
          <div className="grid">
            {person.media.map((item) => (
              <MediaCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
