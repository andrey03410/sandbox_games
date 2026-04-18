class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)

    @property
    def message(self) -> str:
        return str(self)


class BadRequest(DomainError):
    status_code = 400
    code = "bad_request"


class Unauthorized(DomainError):
    status_code = 401
    code = "unauthorized"


class Forbidden(DomainError):
    status_code = 403
    code = "forbidden"


class NotFound(DomainError):
    status_code = 404
    code = "not_found"


class Conflict(DomainError):
    status_code = 409
    code = "conflict"
