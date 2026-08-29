import os
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager
from app.database.db import init_db
from app.routes.scanner import routes as scanner_routes
from app.config import settings

@asynccontextmanager
async def lifespan(app: Starlette):
    await init_db()
    yield

async def read_root(request):
    return JSONResponse({"status": "DealHunter AI Backend Running"})

app = Starlette(
    debug=False,
    lifespan=lifespan,
    routes=[
        Route("/", read_root),
        Mount("/api/scanner", routes=scanner_routes)
    ]
)

# Build allowed origins list — always include localhost for local dev,
# plus any production FRONTEND_URL set in the environment.
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in _allowed_origins:
    _allowed_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
