import { useEffect, useState, useRef } from 'react'
import './App.css'

interface Lobby {
  id: number
  name: string
  game_type: string
  players_count: number
  max_players: number
  status: string
}

function App() {
  const [lobbies, setLobbies] = useState<Lobby[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

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
      <p className={connected ? 'status-connected' : 'status-disconnected'}>
        {connected ? 'Connected' : 'Disconnected'}
      </p>

      <div className="lobbies">
        <h2>Lobbies</h2>
        {lobbies.length === 0 ? (
          <p>Loading...</p>
        ) : (
          <ul className="lobby-list">
            {lobbies.map((lobby) => (
              <li key={lobby.id} className="lobby-item">
                <div className="lobby-name">{lobby.name}</div>
                <div className="lobby-info">
                  <span className="game-type">{lobby.game_type}</span>
                  <span className="players">
                    {lobby.players_count}/{lobby.max_players}
                  </span>
                  <span className={`status ${lobby.status}`}>{lobby.status}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default App
