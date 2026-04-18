from enum import StrEnum


class ParticipantRole(StrEnum):
    HOST = "host"
    PLAYER = "player"
    SPECTATOR = "spectator"


class LobbyStatus(StrEnum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
