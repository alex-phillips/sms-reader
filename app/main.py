import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends
from sqlmodel import SQLModel, Session
from .db import engine, get_session
from .parser import parse_sms_xml
from .crud import create_sms, get_all_sms
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    SQLModel.metadata.create_all(engine)
    yield
    # shutdown code here


app = FastAPI(lifespan=lifespan)


@app.post("/upload/")
async def upload_xml(
    file: UploadFile = File(...), session: Session = Depends(get_session)
):
    content = await file.read()
    with open("temp.xml", "wb") as f:
        f.write(content)

    messages = parse_sms_xml("temp.xml")
    for msg in messages:
        create_sms(session, msg)
    return {"imported": len(messages)}


@app.get("/sms/")
def list_sms(session: Session = Depends(get_session)):
    return get_all_sms(session)
