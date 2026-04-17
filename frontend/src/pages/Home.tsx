import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreateLobbyModal } from '../components/CreateLobbyModal'
import { useAuth } from '../auth'

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

export function Home() {
  const { user } = useAuth()
  const navigate = useNavigate()
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

  const handleCreateClick = () => {
    if (!user) {
      navigate('/login?next=/')
      return
    }
    setModalOpen(true)
  }

  return (
    <>
      <div className={`connection-pill ${connected ? 'connected' : 'disconnected'}`}>
        <span className="dot" />
        {connected ? 'Connected' : 'Disconnected'}
      </div>

      <div className="toolbar">
        <button className="primary-btn" onClick={handleCreateClick}>
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
              <li key={lobby.id}>
                <Link to={`/lobby/${lobby.id}`} className="lobby-item lobby-item-link">
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
                </Link>
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
    </>
  )
}
