from src.core.exceptions import BadRequest, Forbidden
from src.games.base_game import BaseGame


class TicTacToe(BaseGame):
    code = "tic_tac_toe"

    def init_state(self, config: dict, player_ids: list[int]) -> dict:
        width = int(config.get("field_width", 3))
        height = int(config.get("field_height", 3))
        win_line = int(config.get("win_line", 3))
        assignments = {str(player_ids[0]): "X", str(player_ids[1]): "O"}
        return {
            "game_code": self.code,
            "width": width,
            "height": height,
            "win_line": win_line,
            "board": [[None for _ in range(width)] for _ in range(height)],
            "assignments": assignments,
            "next_turn": "X",
            "status": "in_progress",
            "winner": None,
            "winning_line": None,
        }

    def apply_move(self, state: dict, user_id: int, move: dict) -> dict:
        row = int(move["row"])
        col = int(move["col"])

        if state["status"] != "in_progress":
            raise BadRequest("game is not in progress")
        symbol = state["assignments"].get(str(user_id))
        if symbol is None:
            raise Forbidden("you are not a player in this game")
        if symbol != state["next_turn"]:
            raise BadRequest("not your turn")
        if not self._in_bounds(state, row, col):
            raise BadRequest("cell out of bounds")
        if state["board"][row][col] is not None:
            raise BadRequest("cell already taken")

        state["board"][row][col] = symbol
        line = self._check_win(state, row, col, symbol)
        if line is not None:
            state["status"] = "finished"
            state["winner"] = symbol
            state["winning_line"] = line
            return state

        any_empty = any(cell is None for r in state["board"] for cell in r)
        if not any_empty:
            state["status"] = "finished"
            state["winner"] = "draw"
            return state

        state["next_turn"] = "O" if symbol == "X" else "X"
        return state

    @staticmethod
    def _in_bounds(state: dict, r: int, c: int) -> bool:
        return 0 <= r < state["height"] and 0 <= c < state["width"]

    @classmethod
    def _check_win(
        cls, state: dict, row: int, col: int, symbol: str
    ) -> list[list[int]] | None:
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = [(row, col)]
            r, c = row + dr, col + dc
            while cls._in_bounds(state, r, c) and state["board"][r][c] == symbol:
                line.append((r, c))
                r, c = r + dr, c + dc
            r, c = row - dr, col - dc
            while cls._in_bounds(state, r, c) and state["board"][r][c] == symbol:
                line.append((r, c))
                r, c = r - dr, c - dc
            if len(line) >= state["win_line"]:
                return [list(p) for p in sorted(line)]
        return None
