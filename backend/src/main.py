from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.auth.routes import router as auth_router
from src.core.exceptions import DomainError
from src.core.settings import settings
from src.games.routes import router as games_router
from src.lobbies.routes import router as lobbies_router
from src.lobbies.ws import router as ws_router

app = FastAPI(title="Sandbox Games")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )

app.include_router(auth_router)
app.include_router(games_router)
app.include_router(lobbies_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
