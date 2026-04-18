from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.games.state import BaseState

StateT = TypeVar("StateT", bound=BaseState)


class BaseGame(ABC, Generic[StateT]):
    code: str = ""

    @abstractmethod
    def init_state(self, config: dict, player_ids: list[int]) -> StateT: ...

    @abstractmethod
    def apply_move(self, state: StateT, user_id: int, move: dict) -> StateT: ...
