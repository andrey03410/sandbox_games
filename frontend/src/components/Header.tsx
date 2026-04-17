import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Avatar } from './Avatar'

export function Header() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    signOut()
    navigate('/')
  }

  return (
    <header className="header">
      <Link to="/" className="brand">
        Game Platform
      </Link>
      <nav className="header-nav">
        {user ? (
          <>
            <div className="user-badge">
              <Avatar code={user.avatar} size={32} />
              <span className="user-login">{user.login}</span>
            </div>
            <button className="secondary-btn" onClick={handleLogout}>
              Выйти
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="secondary-btn">
              Войти
            </Link>
            <Link to="/register" className="primary-btn">
              Регистрация
            </Link>
          </>
        )}
      </nav>
    </header>
  )
}
