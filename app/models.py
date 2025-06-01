import uuid
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    sms = "sms"
    mms = "mms"


class Direction(str, Enum):
    inbox = "inbox"
    sent = "sent"


class ConversationContactLink(SQLModel, table=True):
    conversation_id: int = Field(foreign_key="conversation.id", primary_key=True)
    contact_id: int = Field(foreign_key="contact.id", primary_key=True)


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = None
    messages: List["Message"] = Relationship(back_populates="conversation")
    contacts: List["Contact"] = Relationship(
        back_populates="conversations", link_model=ConversationContactLink
    )


class Contact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    address: str = Field(unique=True, index=True)
    contact_name: Optional[str] = None

    conversations: List[Conversation] = Relationship(
        back_populates="contacts", link_model=ConversationContactLink
    )
    messages: List["Message"] = Relationship(back_populates="contact")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime  # Unix timestamp in milliseconds
    type: MessageType
    direction: Direction
    text: Optional[str] = None

    contact_id: int = Field(foreign_key="contact.id")
    contact: Optional[Contact] = Relationship(back_populates="messages")

    conversation_id: int = Field(foreign_key="conversation.id")
    conversation: Conversation = Relationship(back_populates="messages")

    media: List["Media"] = Relationship(back_populates="message")


class Media(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="message.id")
    content_type: Optional[str] = None
    filename: Optional[str] = None
    file_path: Optional[str] = None

    message: Optional["Message"] = Relationship(back_populates="media")
