import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_URL, apiFetch } from '../api'
import { useAuth } from '../auth'
import { Avatar } from '../components/Avatar'

interface Participant {
  user_id: number
  login: string
  avatar: string
  role: 'host' | 'player' | 'spectator'
  joined_at: string | null
}

interface LobbyInfo {
  id: number
  name: string
  game_code: string
  game_name: string
  config: Record<string, unknown>
  config_schema: { min_players?: number; max_players?: number; fields?: { name: string; label: string }[] }
  max_players: number
  status_code: string
  status_name: string
  created_by: number
  creator_login: string
  players_count: number
}

interface TicTacToeState {
  game_code: 'tic_tac_toe'
  width: number
  height: number
  win_line: number
  board: (string | null)[][]
  assignments: Record<string, 'X' | 'O'>
  next_turn: 'X' | 'O'
  status: 'in_progress' | 'finished'
  winner: 'X' | 'O' | 'draw' | null
  winning_line: [number, number][] | null
}

interface Snapshot {
  lobby: LobbyInfo
  participants: Participant[]
  game_state: TicTacToeState | null
}

export function LobbyDetail() {
  const { id } = useParams<{ id: string }>()
  const lobbyId = Number(id)
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const wsRef = useRef<WebSocket | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!user || !token || !lobbyId) return
    const url = `${API_URL.replace(/^http/, 'ws')}/ws/lobby/${lobbyId}?token=${encodeURIComponent(
      token,
    )}`
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => setWsConnected(true)
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'snapshot') setSnapshot(msg.data)
      if (msg.type === 'error') setError(msg.detail ?? 'unknown error')
    }
    ws.onclose = () => setWsConnected(false)
    return () => ws.close()
  }, [user, token, lobbyId])

  if (!user) {
    return (
      <div className="lobby-detail">
        <p className="empty">Войдите, чтобы зайти в лобби.</p>
        <button className="primary-btn" onClick={() => navigate(`/login?next=/lobby/${lobbyId}`)}>
          Войти
        </button>
      </div>
    )
  }

  if (!snapshot) {
    return (
      <div className="lobby-detail">
        <p className="empty">Загружаем лобби…</p>
      </div>
    )
  }

  const { lobby, participants, game_state } = snapshot
  const me = participants.find((p) => p.user_id === user.id)
  const isHost = lobby.created_by === user.id
  const playerCount = participants.filter((p) => p.role === 'host' || p.role === 'player').length
  const minPlayers = lobby.config_schema.min_players ?? 2
  const maxPlayers = lobby.config_schema.max_players ?? 2
  const canStart = isHost && lobby.status_code === 'waiting' && playerCount >= minPlayers

  const act = async (path: string, body?: unknown) => {
    setBusy(true)
    setError(null)
    try {
      await apiFetch(path, { method: 'POST', token, body: body ?? {} })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const joinAsPlayer = () => act(`/api/lobbies/${lobby.id}/join`, { role: 'player' })
  const joinAsSpectator = () => act(`/api/lobbies/${lobby.id}/join`, { role: 'spectator' })
  const leave = () => act(`/api/lobbies/${lobby.id}/leave`)
  const start = () => act(`/api/lobbies/${lobby.id}/start`)
  const move = (row: number, col: number) =>
    act(`/api/lobbies/${lobby.id}/move`, { row, col })

  const playerSlotsLeft = maxPlayers - playerCount
  const alreadyInLobby = me !== undefined

  return (
    <div className="lobby-detail">
      <button className="link-btn" onClick={() => navigate('/')}>
        ← К списку лобби
      </button>

      <header className="lobby-header">
        <h2>{lobby.name}</h2>
        <div className="lobby-header-meta">
          <span className="chip game">{lobby.game_name}</span>
          <span className={`chip status ${lobby.status_code}`}>{lobby.status_name}</span>
          <span className="chip players">
            Игроков: {playerCount}/{maxPlayers}
          </span>
          {wsConnected ? (
            <span className="chip status waiting">WS: on</span>
          ) : (
            <span className="chip status finished">WS: off</span>
          )}
        </div>
        <div className="lobby-creator">Создатель: {lobby.creator_login}</div>
      </header>

      <section className="lobby-config">
        <h3>Настройки игры</h3>
        <dl className="config-list">
          {lobby.config_schema.fields?.map((f) => (
            <div key={f.name} className="config-row">
              <dt>{f.label}</dt>
              <dd>{String((lobby.config as Record<string, unknown>)[f.name] ?? '—')}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="participants">
        <h3>Участники</h3>
        <ul className="participant-list">
          {participants.map((p) => {
            const symbol = game_state?.assignments?.[String(p.user_id)]
            return (
              <li key={p.user_id} className={`participant role-${p.role}`}>
                <Avatar code={p.avatar} size={36} />
                <div className="participant-meta">
                  <div className="participant-login">{p.login}</div>
                  <div className="participant-role">
                    {p.role === 'host' && 'Хост'}
                    {p.role === 'player' && 'Игрок'}
                    {p.role === 'spectator' && 'Наблюдатель'}
                    {symbol && <span className="symbol-badge"> • играет за {symbol}</span>}
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </section>

      {error && <div className="form-error">{error}</div>}

      <section className="lobby-actions">
        {!alreadyInLobby && lobby.status_code === 'waiting' && (
          <>
            <button
              className="primary-btn"
              onClick={joinAsPlayer}
              disabled={busy || playerSlotsLeft <= 0}
              title={playerSlotsLeft <= 0 ? 'Мест игроков нет' : ''}
            >
              Присоединиться игроком
            </button>
            <button className="secondary-btn" onClick={joinAsSpectator} disabled={busy}>
              Наблюдать
            </button>
          </>
        )}
        {!alreadyInLobby && lobby.status_code !== 'waiting' && (
          <button className="secondary-btn" onClick={joinAsSpectator} disabled={busy}>
            Наблюдать
          </button>
        )}
        {isHost && lobby.status_code === 'waiting' && (
          <button
            className="primary-btn"
            onClick={start}
            disabled={busy || !canStart}
            title={!canStart ? `Нужно минимум ${minPlayers} игроков` : ''}
          >
            Начать игру
          </button>
        )}
        {alreadyInLobby && !isHost && (
          <button className="secondary-btn" onClick={leave} disabled={busy}>
            Покинуть лобби
          </button>
        )}
      </section>

      {game_state && <GameBoard state={game_state} me={user.id} onMove={move} disabled={busy} />}
    </div>
  )
}

function GameBoard({
  state,
  me,
  onMove,
  disabled,
}: {
  state: TicTacToeState
  me: number
  onMove: (row: number, col: number) => void
  disabled: boolean
}) {
  const mySymbol = state.assignments[String(me)]
  const isMyTurn = state.status === 'in_progress' && mySymbol === state.next_turn
  const winningSet = new Set(
    (state.winning_line ?? []).map(([r, c]) => `${r},${c}`),
  )

  let banner: string
  if (state.status === 'finished') {
    if (state.winner === 'draw') banner = 'Ничья!'
    else if (mySymbol && state.winner === mySymbol) banner = 'Вы победили!'
    else if (mySymbol) banner = 'Вы проиграли'
    else banner = `Победил ${state.winner}`
  } else if (mySymbol) {
    banner = isMyTurn ? `Ваш ход (${mySymbol})` : `Ход соперника (${state.next_turn})`
  } else {
    banner = `Ход игрока ${state.next_turn}`
  }

  return (
    <section className="game-board-section">
      <div className={`game-banner ${state.status}`}>{banner}</div>
      <div
        className="board"
        style={{
          gridTemplateColumns: `repeat(${state.width}, minmax(0, 1fr))`,
          maxWidth: `${Math.min(420, state.width * 70)}px`,
        }}
      >
        {state.board.map((rowCells, r) =>
          rowCells.map((cell, c) => {
            const highlighted = winningSet.has(`${r},${c}`)
            const clickable = isMyTurn && cell === null && !disabled
            return (
              <button
                key={`${r}-${c}`}
                className={`cell ${cell ? `cell-${cell.toLowerCase()}` : ''} ${
                  highlighted ? 'cell-win' : ''
                }`}
                onClick={() => clickable && onMove(r, c)}
                disabled={!clickable}
              >
                {cell ?? ''}
              </button>
            )
          }),
        )}
      </div>
    </section>
  )
}
