from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from uuid import UUID
from app.models import Contact, Message, Media, Conversation
from app.db import get_session
from pathlib import Path
from starlette.responses import Response
import mimetypes
import hashlib
import os
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import selectinload

router = APIRouter()
MEDIA_DIR = Path("media")


def serialize_message_with_media(msg: Message, session: Session):
    contact = session.get(Contact, msg.contact_id)

    return {
        "id": msg.id,
        "direction": msg.direction,
        "text": msg.text,
        "date": msg.date,
        "contact": contact.contact_name if contact.contact_name else contact.address,
        "media": (
            [
                {
                    "id": m.id,
                    "filename": m.filename,
                    "content_type": m.content_type,
                }
                for m in msg.media
            ]
        ),
    }


# GET /contacts/?search=...
@router.get("/conversations")
def list_conversations(
    search: str | None = None, session: Session = Depends(get_session)
):
    query = select(Conversation)
    if search:
        query = query.where((Conversation.name.ilike(f"%{search}%")))

    results = session.exec(query).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "contacts": [
                {
                    "id": contact.id,
                    "address": contact.address,
                    "contact_name": contact.contact_name,
                }
                for contact in c.contacts
            ],
        }
        for c in results
    ]


# GET /conversation/{conversation_id}
@router.get("/conversation/{conversation_id}")
def get_conversation_by_id(
    conversation_id: int, session: Session = Depends(get_session)
):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conversation.id,
        "name": conversation.name,
        "contacts": [
            {
                "id": contact.id,
                "address": contact.address,
                "contact_name": contact.contact_name,
            }
            for contact in conversation.contacts
        ],
    }


# GET /contacts/{conversation_id}/messages
@router.get("/conversation/{conversation_id}/messages")
def get_messages_for_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    start_before_message_id: int | None = Query(None),
    start_after_message_id: int | None = Query(None),
):
    base_query = select(Message).where(Message.conversation_id == conversation_id)

    total = session.exec(
        select(func.count()).where(Message.conversation_id == conversation_id)
    ).one()

    if start_before_message_id:
        # Load messages older
        reference = session.get(Message, start_before_message_id)
        if reference:
            base_query = base_query.where(Message.date < reference.date)

        # Order descending to get older messages
        query = base_query.options(selectinload(Message.media)).order_by(
            Message.date.desc()
        )
        messages = session.exec(query.limit(limit)).all()
    elif start_after_message_id:
        # Load messages newer
        reference = session.get(Message, start_after_message_id)
        if reference:
            base_query = base_query.where(Message.date > reference.date)

        # Order ascending to get newer messages in chronological order
        query = base_query.options(selectinload(Message.media)).order_by(
            Message.date.asc()
        )
        messages = session.exec(query.limit(limit)).all()
        # Reverse messages so they show newest last in UI
        messages.reverse()
    else:
        # Initial load or no cursor, order descending to get most recent messages
        query = base_query.options(selectinload(Message.media)).order_by(
            Message.date.desc()
        )
        messages = session.exec(query.limit(limit)).all()

    has_more = False
    has_newer = False

    if messages:
        oldest_date = messages[0].date
        newest_date = messages[-1].date

        result = session.exec(
            select(func.count()).where(
                (Message.conversation_id == conversation_id)
                & (Message.date < oldest_date)
            )
        )
        has_more = result.one() > 0

        result = session.exec(
            select(func.count()).where(
                Message.conversation_id == conversation_id,
                Message.date > newest_date,
            )
        )
        has_newer = result.one() > 0

    return {
        "messages": [serialize_message_with_media(m, session) for m in messages],
        "total": total,
        "has_more": has_more,
        "has_newer": has_newer,
    }


@router.get("/conversation/{conversation_id}/media")
def get_media_for_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total = session.exec(
        select(func.count(Media.id))
        .join(Message)
        .where(Message.conversation_id == conversation_id)
    ).one()

    media_items = session.exec(
        select(Media)
        .join(Message)
        .options(selectinload(Media.message))
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.date.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    has_more = offset + limit < total

    def serialize_media(media: Media):
        message = media.message
        contact = message.contact if message else None
        return {
            "id": media.id,
            "content_type": media.content_type,
            "filename": media.filename,
            "message_id": message.id if message else None,
            "date": message.date if message else None,
            "contact_id": contact.id if contact else None,
            "contact_name": contact.contact_name if contact else None,
            "contact_address": contact.address if contact else None,
        }

    return {
        "media": [serialize_media(m) for m in media_items],
        "total": total,
        "has_more": has_more,
    }


# GET /contacts/{conversation_id}/search
@router.get("/conversation/{conversation_id}/search")
def search_messages_for_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    query: str | None = Query(None),
):
    messages = session.exec(
        select(Message)
        .options(selectinload(Message.media))
        .where(Message.conversation_id == conversation_id)
        .where(Message.text.ilike(f"%{query}%"))
        .order_by(Message.date.desc())
    ).all()

    return [serialize_message_with_media(m, session) for m in messages]


# GET /messages/{message_id}
@router.get("/messages/{message_id}")
def get_message_by_id(message_id: int, session: Session = Depends(get_session)):
    statement = (
        select(Message)
        .where(Message.id == message_id)
        .options(selectinload(Message.media))
    )
    message = session.exec(statement).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "id": message.id,
        "contact_id": message.contact_id,
        "direction": message.direction,
        "date": message.date.isoformat(),
        "text": message.text,
        "media": [
            {
                "id": media.id,
                "content_type": media.content_type,
                "filename": media.file_path.name,
                "url": f"/media/{media.id}/cache",
            }
            for media in message.media
        ],
    }


# GET /media/{media_id}
@router.get("/media/{media_id}")
def get_media_metadata(media_id: str, session: Session = Depends(get_session)):
    media = session.get(Media, str(media_id))
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    message = session.get(Message, media.message_id)
    contact = session.get(Contact, message.contact_id) if message else None

    return {
        "id": str(media.id),
        "content_type": media.content_type,
        "filename": media.file_path.name,
        "message_id": message.id if message else None,
        "message_timestamp": message.timestamp if message else None,
        "contact_id": contact.id if contact else None,
        "contact_name": contact.name if contact else None,
        "contact_address": contact.address if contact else None,
    }


# GET /media/{media_id}/cache
@router.get("/media/{media_id}/cache")
def serve_media_file(media_id: int, session: Session = Depends(get_session)):
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if not os.path.exists(media.file_path):
        raise HTTPException(status_code=404, detail="Media file missing on disk")

    # Compute ETag (e.g. SHA256 hash of file)
    file_hash = hashlib.sha256(Path(media.file_path).read_bytes()).hexdigest()
    content_type = (
        media.content_type
        or mimetypes.guess_type(media.file_path)[0]
        or "application/octet-stream"
    )

    # Add ETag + Last-Modified
    last_modified = datetime.utcfromtimestamp(os.stat(media.file_path).st_mtime)
    headers = {
        "ETag": file_hash,
        "Last-Modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }

    return FileResponse(
        media.file_path,
        media_type=content_type,
        headers=headers,
    )
