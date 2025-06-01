# main.py
from fastapi import FastAPI
from app.api import router
from app.models import SQLModel
from app.db import engine
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request
from pathlib import Path
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    SQLModel.metadata.create_all(engine)
    yield
    # run shutdown code after yield


app = FastAPI(title="SMS API", lifespan=lifespan)


app.include_router(router, prefix="/api")

# Mount static files from frontend build
frontend_dist_path = Path(__file__).parent / "frontend" / "dist"
app.mount(
    "/assets", StaticFiles(directory=frontend_dist_path / "assets"), name="static"
)


# Catch-all route for frontend (serves index.html)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str, request: Request):
    index_file = frontend_dist_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"detail": "Frontend not built or index.html not found"}
