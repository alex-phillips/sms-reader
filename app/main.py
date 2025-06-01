from fastapi import FastAPI
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from .db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    SQLModel.metadata.create_all(engine)
    yield
    # shutdown code here


app = FastAPI(lifespan=lifespan)
