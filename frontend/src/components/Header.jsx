import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import HeaderSearch from './HeaderSearch'

function navClass({ isActive }) {
  return isActive ? 'active' : ''
}

function PlusIcon() {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

function CogIcon() {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    setQuery(params.get('q') || '')
  }, [location.pathname, location.search])

  function handleSearch(e) {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`)
    } else if (location.pathname === '/search') {
      navigate('/search')
    }
  }

  return (
    <>
      <header className="header">
        <div className="header-inner">
          <div className="header-start">
            <button
              type="button"
              className="menu-toggle"
              aria-label="Open menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span />
              <span />
              <span />
            </button>

            <NavLink to="/" className="logo">
              Movie <span>Reel</span>
            </NavLink>
          </div>

          <nav className="nav nav-center nav-desktop" aria-label="Main">
            <NavLink to="/" end className={navClass}>
              Home
            </NavLink>
            <NavLink to="/movies" className={navClass}>
              Movies
            </NavLink>
            <NavLink to="/tv" className={navClass}>
              TV Shows
            </NavLink>
            <HeaderSearch
              className="header-search header-search-desktop"
              query={query}
              onChange={setQuery}
              onSubmit={handleSearch}
            />
          </nav>

          <nav className="nav nav-actions nav-desktop" aria-label="Actions">
            <NavLink to="/add" className={navClass}>
              <PlusIcon />
              Add
            </NavLink>
            <NavLink to="/settings" className={navClass}>
              <CogIcon />
              Settings
            </NavLink>
          </nav>
        </div>

        <HeaderSearch
          className="header-search header-search-mobile"
          query={query}
          onChange={setQuery}
          onSubmit={handleSearch}
        />
      </header>

      <div
        className={`menu-overlay ${menuOpen ? 'open' : ''}`}
        onClick={() => setMenuOpen(false)}
        aria-hidden={!menuOpen}
      />

      <nav
        className={`slide-menu ${menuOpen ? 'open' : ''}`}
        aria-label="Mobile menu"
        aria-hidden={!menuOpen}
      >
        <div className="slide-menu-header">
          <span className="slide-menu-title">Menu</span>
          <button
            type="button"
            className="menu-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            ×
          </button>
        </div>
        <NavLink to="/" end className={navClass} onClick={() => setMenuOpen(false)}>
          Home
        </NavLink>
        <NavLink to="/movies" className={navClass} onClick={() => setMenuOpen(false)}>
          Movies
        </NavLink>
        <NavLink to="/tv" className={navClass} onClick={() => setMenuOpen(false)}>
          TV Shows
        </NavLink>
        <NavLink to="/add" className={navClass} onClick={() => setMenuOpen(false)}>
          <PlusIcon />
          Add
        </NavLink>
        <NavLink to="/settings" className={navClass} onClick={() => setMenuOpen(false)}>
          <CogIcon />
          Settings
        </NavLink>
      </nav>
    </>
  )
}
