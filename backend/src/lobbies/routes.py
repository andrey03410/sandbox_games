import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.auth.dependencies import current_user_id
from src.core.db import get_session
from src.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from src.games.enums import GameStatus
from src.games.models import Game
from src.games.registry import get_game
from src.lobbies.enums import LobbyStatus, ParticipantRole
from src.lobbies.models import Lobby, LobbyParticipant
from src.lobbies.schemas.create_lobby_request import CreateLobbyRequest
from src.lobbies.schemas.join_request import JoinRequest
from src.lobbies.schemas.move_request import MoveRequest
from src.lobbies.service import (
    active_games,
    broadcast_snapshot,
    build_snapshot,
    count_active_participants,
    get_lobby_row,
    list_lobby_views,
    status_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lobbies", tags=["lobbies"])

JOINABLE_ROLES = {ParticipantRole.PLAYER, ParticipantRole.SPECTATOR}


@router.get("")
def list_lobbies(session: Session = Depends(get_session)):
    return list_lobby_views(session)


@router.post("", status_code=201)
async def create_lobby(
    req: CreateLobbyRequest,
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    game_id = session.scalar(select(Game.id).where(Game.code == req.game_code))
    if game_id is None:
        raise BadRequest(f"unknown game_code: {req.game_code}")

    lobby = Lobby(
        name=req.name,
        game_id=game_id,
        status_id=status_id(session, LobbyStatus.WAITING),
        created_by=user_id,
        config=req.config,
        max_players=req.max_players,
    )
    session.add(lobby)
    session.flush()

    session.add(
        LobbyParticipant(
            lobby_id=lobby.id, user_id=user_id, role=ParticipantRole.HOST
        )
    )
    session.commit()
    logger.info(
        "lobby created id=%s game=%s host=%s max_players=%s",
        lobby.id, req.game_code, user_id, req.max_players,
    )
    return {"id": lobby.id}


@router.get("/{lobby_id}")
def get_lobby(lobby_id: int, user_id: int = Depends(current_user_id)):
    snapshot = build_snapshot(lobby_id)
    if snapshot is None:
        raise NotFound("lobby not found")
    return snapshot


@router.post("/{lobby_id}/join")
async def join_lobby(
    lobby_id: int,
    req: JoinRequest,
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    try:
        role = ParticipantRole(req.role)
    except ValueError:
        raise BadRequest("invalid role")
    if role not in JOINABLE_ROLES:
        raise BadRequest("invalid role")

    row = get_lobby_row(session, lobby_id)
    if row is None:
        raise NotFound("lobby not found")

    existing = session.scalar(
        select(LobbyParticipant).where(
            LobbyParticipant.lobby_id == lobby_id,
            LobbyParticipant.user_id == user_id,
        )
    )
    if existing is not None:
        if existing.role == ParticipantRole.HOST:
            raise BadRequest("you are the host")
        if existing.role != role:
            existing.role = role
    else:
        if role is ParticipantRole.PLAYER:
            max_players = int(
                row.config_schema.get("max_players", row.max_players)
            )
            taken = count_active_participants(session, lobby_id)
            if taken >= max_players:
                raise Conflict("no free player slot")
        session.add(
            LobbyParticipant(lobby_id=lobby_id, user_id=user_id, role=role)
        )
    session.commit()

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/leave")
async def leave_lobby(
    lobby_id: int,
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    row = get_lobby_row(session, lobby_id)
    if row is None:
        raise NotFound("lobby not found")
    if row.created_by == user_id:
        raise BadRequest("host cannot leave")

    session.execute(
        LobbyParticipant.__table__.delete().where(
            LobbyParticipant.lobby_id == lobby_id,
            LobbyParticipant.user_id == user_id,
        )
    )
    session.commit()

    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/start")
async def start_game(
    lobby_id: int,
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    row = get_lobby_row(session, lobby_id)
    if row is None:
        raise NotFound("lobby not found")
    if row.created_by != user_id:
        raise Forbidden("only host can start")
    if row.status_code != LobbyStatus.WAITING:
        raise BadRequest("game already started or finished")

    player_ids = list(
        session.scalars(
            select(LobbyParticipant.user_id)
            .where(
                LobbyParticipant.lobby_id == lobby_id,
                LobbyParticipant.role.in_(
                    [ParticipantRole.HOST, ParticipantRole.PLAYER]
                ),
            )
            .order_by(LobbyParticipant.joined_at)
        )
    )

    min_players = int(row.config_schema.get("min_players", 2))
    max_players = int(row.config_schema.get("max_players", min_players))
    if len(player_ids) < min_players:
        raise BadRequest(f"not enough players: {len(player_ids)}/{min_players}")

    game = get_game(row.game_code)
    if game is None:
        raise BadRequest(f"unsupported game: {row.game_code}")
    state = game.init_state(row.config, player_ids[:max_players])

    active_games[lobby_id] = state
    session.execute(
        update(Lobby)
        .where(Lobby.id == lobby_id)
        .values(status_id=status_id(session, LobbyStatus.IN_PROGRESS))
    )
    session.commit()

    logger.info(
        "lobby started id=%s game=%s players=%s",
        lobby_id, row.game_code, player_ids,
    )
    await broadcast_snapshot(lobby_id)
    return {"ok": True}


@router.post("/{lobby_id}/move")
async def make_move(
    lobby_id: int,
    req: MoveRequest,
    user_id: int = Depends(current_user_id),
    session: Session = Depends(get_session),
):
    state = active_games.get(lobby_id)
    if state is None:
        raise NotFound("no active game")
    game = get_game(state.game_code)
    if game is None:
        raise RuntimeError(f"game impl missing: {state.game_code}")
    game.apply_move(state, user_id, req.model_dump())
    logger.info(
        "move applied lobby=%s user=%s move=%s status=%s",
        lobby_id, user_id, req.model_dump(), state.status,
    )

    if state.status is GameStatus.FINISHED:
        session.execute(
            update(Lobby)
            .where(Lobby.id == lobby_id)
            .values(status_id=status_id(session, LobbyStatus.FINISHED))
        )
        session.commit()
        logger.info("lobby finished id=%s winner=%s", lobby_id, state.winner)

    await broadcast_snapshot(lobby_id)
    return {"ok": True}
