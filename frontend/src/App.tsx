import { useEffect, useState, useRef } from 'react'
import './App.css'

interface Lobby {
  id: number
  name: string
  game_code: string
  game_name: string
  config: Record<string, unknown>
  players_count: number
  max_players: number
  status_code: string
  status_name: string
}

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

const API_URL = 'http://localhost:8000'

function CreateLobbyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [games, setGames] = useState<Game[]>([])
  const [name, setName] = useState('')
  const [gameCode, setGameCode] = useState('')
  const [config, setConfig] = useState<Record<string, unknown>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/games`)
      .then((r) => r.json())
      .then((data: Game[]) => {
        setGames(data)
        if (data.length > 0) {
          applyGame(data[0], setGameCode, setConfig)
        }
      })
      .catch((e) => setError(`Не удалось загрузить список игр: ${e.message}`))
  }, [])

  const selectedGame = games.find((g) => g.code === gameCode)
  const fields = selectedGame?.config_schema.fields ?? []

  const handleGameChange = (code: string) => {
    const g = games.find((x) => x.code === code)
    if (g) applyGame(g, setGameCode, setConfig)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const resp = await fetch(`${API_URL}/api/lobbies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          game_code: gameCode,
          config,
          max_players: 10,
        }),
      })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(text || `HTTP ${resp.status}`)
      }
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
              onChange={(e) => handleGameChange(e.target.value)}
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

function applyGame(
  g: Game,
  setCode: (c: string) => void,
  setCfg: (c: Record<string, unknown>) => void,
) {
  setCode(g.code)
  const defaults: Record<string, unknown> = {}
  for (const f of g.config_schema.fields ?? []) defaults[f.name] = f.default
  setCfg(defaults)
}

function App() {
  const [lobbies, setLobbies] = useState<Lobby[]>([])
  const [connected, setConnected] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const refreshLobbies = () => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'get_lobbies' }))
    }
  }

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      ws.send(JSON.stringify({ type: 'get_lobbies' }))
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (message.type === 'lobbies_list') {
        setLobbies(message.data)
      }
    }

    ws.onclose = () => setConnected(false)

    return () => ws.close()
  }, [])

  return (
    <div className="app">
      <h1>Game Platform</h1>
      <div className={`connection-pill ${connected ? 'connected' : 'disconnected'}`}>
        <span className="dot" />
        {connected ? 'Connected' : 'Disconnected'}
      </div>

      <div className="toolbar">
        <button className="primary-btn" onClick={() => setModalOpen(true)}>
          Создать лобби
        </button>
      </div>

      <div className="lobbies">
        <h2>Лобби</h2>
        {lobbies.length === 0 ? (
          <p className="empty">Пока нет ни одного лобби</p>
        ) : (
          <ul className="lobby-list">
            {lobbies.map((lobby) => (
              <li key={lobby.id} className="lobby-item">
                <div className="lobby-name">{lobby.name}</div>
                <div className="lobby-info">
                  <span className="chip game">{lobby.game_name}</span>
                  <span className="chip players">
                    {lobby.players_count}/{lobby.max_players}
                  </span>
                  <span className={`chip status ${lobby.status_code}`}>
                    {lobby.status_name}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {modalOpen && (
        <CreateLobbyModal
          onClose={() => setModalOpen(false)}
          onCreated={refreshLobbies}
        />
      )}
    </div>
  )
}

export default App
