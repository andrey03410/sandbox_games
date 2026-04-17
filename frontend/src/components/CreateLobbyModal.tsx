import { useEffect, useState } from 'react'
import { apiFetch } from '../api'
import { useAuth } from '../auth'

interface ConfigField {
  name: string
  type: 'int' | string
  label: string
  default: number | string
  min?: number
  max?: number
}

interface Game {
  id: number
  code: string
  name: string
  config_schema: { fields?: ConfigField[] }
}

export function CreateLobbyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const { token } = useAuth()
  const [games, setGames] = useState<Game[]>([])
  const [name, setName] = useState('')
  const [gameCode, setGameCode] = useState('')
  const [config, setConfig] = useState<Record<string, unknown>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<Game[]>('/api/games')
      .then((data) => {
        setGames(data)
        if (data.length > 0) applyGame(data[0])
      })
      .catch((e) => setError(`Не удалось загрузить список игр: ${e.message}`))
  }, [])

  const applyGame = (g: Game) => {
    setGameCode(g.code)
    const defaults: Record<string, unknown> = {}
    for (const f of g.config_schema.fields ?? []) defaults[f.name] = f.default
    setConfig(defaults)
  }

  const selected = games.find((g) => g.code === gameCode)
  const fields = selected?.config_schema.fields ?? []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await apiFetch('/api/lobbies', {
        method: 'POST',
        token,
        body: { name, game_code: gameCode, config, max_players: 10 },
      })
      onCreated()
      onClose()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Создать лобби</h2>
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span>Название лобби</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={1}
              maxLength={100}
              autoFocus
            />
          </label>

          <label className="field">
            <span>Игра</span>
            <select
              value={gameCode}
              onChange={(e) => {
                const g = games.find((x) => x.code === e.target.value)
                if (g) applyGame(g)
              }}
              required
            >
              {games.map((g) => (
                <option key={g.code} value={g.code}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>

          <div className="config-block" key={gameCode}>
            {fields.map((f) => (
              <label key={f.name} className="field">
                <span>{f.label}</span>
                <input
                  type={f.type === 'int' ? 'number' : 'text'}
                  value={(config[f.name] ?? '') as string | number}
                  min={f.min}
                  max={f.max}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      [f.name]:
                        f.type === 'int' ? Number(e.target.value) : e.target.value,
                    })
                  }
                  required
                />
              </label>
            ))}
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="secondary-btn"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={submitting || !name || !gameCode}
              className="primary-btn"
            >
              {submitting ? 'Создаём…' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
