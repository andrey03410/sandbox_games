import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'
import { useAuth, type User } from '../auth'
import { AVATARS, Avatar } from '../components/Avatar'

export function Register() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [avatar, setAvatar] = useState<string>(AVATARS[0].code)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const data = await apiFetch<{ token: string; user: User }>(
        '/api/auth/register',
        {
          method: 'POST',
          body: { login, password, avatar },
        },
      )
      signIn(data.token, data.user)
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>Регистрация</h2>
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span>Логин (3–50 символов)</span>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              minLength={3}
              maxLength={50}
              autoFocus
              autoComplete="username"
            />
          </label>
          <label className="field">
            <span>Пароль (минимум 6 символов)</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete="new-password"
            />
          </label>

          <div className="field">
            <span>Аватар</span>
            <div className="avatar-grid">
              {AVATARS.map((a) => (
                <button
                  key={a.code}
                  type="button"
                  className={`avatar-option ${avatar === a.code ? 'selected' : ''}`}
                  onClick={() => setAvatar(a.code)}
                  title={a.label}
                >
                  <Avatar code={a.code} size={52} />
                </button>
              ))}
            </div>
          </div>

          {error && <div className="form-error">{error}</div>}

          <button
            type="submit"
            className="primary-btn"
            disabled={submitting || !login || !password}
          >
            {submitting ? 'Регистрируем…' : 'Создать аккаунт'}
          </button>
        </form>
        <p className="auth-switch">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  )
}
