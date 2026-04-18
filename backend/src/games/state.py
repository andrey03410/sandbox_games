from dataclasses import dataclass, field

from src.games.enums import GameStatus


@dataclass
class BaseState:
    game_code: str
    status: GameStatus = GameStatus.IN_PROGRESS
    winner: str | None = None


@dataclass
class TicTacToeState(BaseState):
    width: int = 3
    height: int = 3
    win_line: int = 3
    board: list[list[str | None]] = field(default_factory=list)
    assignments: dict[str, str] = field(default_factory=dict)
    next_turn: str = "X"
    winning_line: list[list[int]] | None = None
