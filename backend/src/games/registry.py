from src.games.base_game import BaseGame
from src.games.tic_tac_toe import TicTacToe


_registry: dict[str, BaseGame] = {}


def register_game(game: BaseGame) -> None:
    _registry[game.code] = game


def get_game(code: str) -> BaseGame | None:
    return _registry.get(code)


register_game(TicTacToe())
