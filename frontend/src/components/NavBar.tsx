import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import Ticker from './Ticker'
import YaleMark from './YaleMark'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <header className="site-header">
      <nav className="nav">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <YaleMark size={42} />
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue · New Haven</small>
          </span>
        </Link>
        <ul className="nav-links">
          {links.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="nav-account">
          {loading ? null : user ? (
            <>
              <span className="nav-user">
                <span className="nav-avatar" aria-hidden="true">
                  {user.first_name.slice(0, 1)}
                </span>
                Hi, {user.first_name}
              </span>
              <button className="btn btn-small btn-outline" onClick={handleLogout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log In</NavLink>
              <NavLink to="/signup" className="btn btn-small">
                Create Account
              </NavLink>
            </>
          )}
        </div>
      </nav>
      <Ticker />
    </header>
  )
}
