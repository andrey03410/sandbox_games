from abc import ABC, abstractmethod


class BaseGame(ABC):
    code: str = ""

    @abstractmethod
    def init_state(self, config: dict, player_ids: list[int]) -> dict:
        ...

    @abstractmethod
    def apply_move(self, state: dict, user_id: int, move: dict) -> dict:
        ...
