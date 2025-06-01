import base64
import csv
import mimetypes
import re
import os
import shutil
from typing import Optional
from datetime import datetime
from pathlib import Path
from sqlmodel import Session, select
from lxml import etree
from sqlalchemy import func
from .models import (
    Message,
    Contact,
    Media,
    MessageType,
    Direction,
    Conversation,
    ConversationContactLink,
)
from .utils import normalize_number

MEDIA_DIR = Path("/data/media")
MEDIA_DIR.mkdir(exist_ok=True)


class Parser:
    session: Session

    def get_or_create_contact(
        self, address: str, name: Optional[str] = None
    ) -> Contact:
        address = normalize_number(address)
        statement = select(Contact).where(Contact.address == address)
        contact = self.session.exec(statement).first()

        if contact:
            if not contact.name and name:
                contact.name = name
                self.session.add(contact)

                self.session.commit()
                self.session.refresh(contact)

        if not contact:
            contact = Contact(address=address, name=name)
            self.session.add(contact)
            self.session.commit()
            self.session.refresh(contact)

        return contact

    def get_conversation_by_contacts(
        self, contact_ids: list[int]
    ) -> Optional[Conversation]:
        # First, get conversations where contacts count matches
        possible_conversations = self.session.exec(
            select(Conversation)
            .join(ConversationContactLink)
            .where(ConversationContactLink.contact_id.in_(contact_ids))
            .group_by(Conversation.id)
            .having(func.count(ConversationContactLink.contact_id) == len(contact_ids))
        ).all()

        # Find convo where all contacts match
        for convo in possible_conversations:
            convo_contact_ids = {contact.id for contact in convo.contacts}
            if convo_contact_ids == set(contact_ids):
                conversation_name = ", ".join(
                    contact.name if contact.name else contact.address
                    for contact in sorted(convo.contacts, key=lambda c: c.id)
                )

                if convo.name != conversation_name:
                    convo.name = conversation_name
                    self.session.add(convo)
                    self.session.commit()

                return convo

        return None

    def get_or_create_conversation(self, contacts: list[Contact]) -> Conversation:
        conversation_name = ", ".join(
            contact.name if contact.name else contact.address
            for contact in sorted(contacts, key=lambda c: c.id)
        )

        convo = self.get_conversation_by_contacts([contact.id for contact in contacts])
        if convo:
            if convo.name != conversation_name:
                convo.name = conversation_name
                self.session.add(convo)
                self.session.commit()

            return convo

        new_convo = Conversation()
        self.session.add(new_convo)
        self.session.commit()  # Must commit first to get an ID

        for contact in contacts:
            self.session.add(
                ConversationContactLink(
                    conversation_id=new_convo.id, contact_id=contact.id
                )
            )

        self.session.commit()
        self.session.refresh(new_convo)

        return new_convo


class SMSBackupAndRestore(Parser):
    def __init__(self, session: Session):
        self.session = session

    def save_media(self, part_elem, message_id: str, index: int) -> Optional[Media]:
        ct = part_elem.attrib.get("ct")
        data = part_elem.attrib.get("data")
        if not data:
            return None

        ext = ct.split("/")[-1]
        filename = f"{message_id}_{index}.{ext}"
        filepath = MEDIA_DIR / filename

        try:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(data))
        except (base64.binascii.Error, ValueError) as e:
            print(f"Failed to decode media part: {e}")
            return None

        return Media(
            message_id=message_id,
            content_type=ct,
            filename=filename,
            file_path=str(filepath),
        )

    def process_sms(self, elem, user_address: str):
        date_ts = int(elem.attrib["date"])
        address = elem.attrib.get("address")
        name = elem.attrib.get("name")
        body = elem.attrib.get("body")
        type_code = int(elem.attrib.get("type", "1"))

        direction = Direction.inbox if type_code == 1 else Direction.sent
        contact = self.get_or_create_contact(address, name)
        conversation = self.get_or_create_conversation([contact])

        from_contact = (
            self.get_or_create_contact(user_address, "Me")
            if direction == Direction.sent
            else contact
        )

        # Dedupe
        exists = self.session.exec(
            select(Message).where(
                Message.contact_id == from_contact.id,
                Message.date == datetime.fromtimestamp(date_ts / 1000),
                Message.text == body,
                Message.conversation_id == conversation.id,
            )
        ).first()

        if not exists:
            msg = Message(
                date=datetime.fromtimestamp(date_ts / 1000),
                type=MessageType.sms,
                direction=direction,
                text=body,
                contact_id=from_contact.id,
                conversation_id=conversation.id,
            )
            self.session.add(msg)

    def process_mms(self, elem, user_address):
        date_ts = int(elem.attrib["date"])
        from_addr = None
        to_addrs = set()

        for addr_elem in elem.findall("./addrs/addr"):
            address = addr_elem.get("address")

            # Skip invalid or system placeholder addrs
            if not address or address.lower() in {
                "insert-address-token",
                "unknown",
            }:
                continue

            address = normalize_number(address)
            type_code = int(addr_elem.get("type", 0))

            if type_code == 137:
                from_addr = address
            # elif type_code == 151:
            else:
                # I did only account for 151, which means 'received', but I'm also seeing
                # MMS messages where all addrs have a type of 130, but the sender consistently
                # had 137. So if it's not 137, let's assume it's a receiving address.
                to_addrs.add(address)

        # Special edge case:
        # If from_addr is the same as one of the to_addrs and there's only one unique address,
        # it's likely "me" is missing and this is a 1:1 with the sender.
        participants = to_addrs | ({from_addr} if from_addr else set())

        if user_address in participants:
            participants.discard(user_address)

        # Assume sender is 'me' if missing
        if not from_addr:
            from_addr = user_address

        from_contact = self.get_or_create_contact(from_addr)
        participants = [self.get_or_create_contact(addr, None) for addr in participants]

        conversation = self.get_or_create_conversation(participants)
        direction = Direction.sent if from_addr == user_address else Direction.inbox

        text_body = None
        media_parts = []

        for part in elem.iter("part"):
            ct = part.attrib.get("ct")
            if ct == "text/plain":
                text_body = part.attrib.get("text", "")
            elif ct.startswith("image/") and "data" in part.attrib:
                media_parts.append(part)

        # Dedupe here
        query = select(Message).where(
            Message.contact_id == from_contact.id,
            Message.date == datetime.fromtimestamp(date_ts / 1000),
        )
        if text_body:
            query = query.where(Message.text == text_body)
        else:
            query = query.where(Message.text.is_(None))

        existing = self.session.exec(query).first()
        if existing:
            elem.clear()
            return

        msg = Message(
            date=datetime.fromtimestamp(date_ts / 1000),
            type=MessageType.mms,
            direction=direction,
            text=text_body,
            contact_id=from_contact.id,
            conversation_id=conversation.id,
        )
        self.session.add(msg)
        self.session.commit()
        self.session.refresh(msg)

        for index, part in enumerate(media_parts):
            media = self.save_media(part, msg.id, index)
            if media:
                self.session.add(media)

    def parse_sms_xml_stream(self, filepath: str, user_address: str = None):
        context = etree.iterparse(
            filepath, events=("end",), tag=("sms", "mms"), huge_tree=True
        )

        user_address = normalize_number(user_address) if user_address else None

        for _, elem in context:
            tag = elem.tag

            if tag == "sms":
                self.process_sms(elem, user_address)

            elif tag == "mms":
                self.process_mms(elem, user_address)

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        self.session.commit()


class CSV(Parser):
    filepath: str

    def __init__(
        self, session: Session, filepath: str, attachments_dir: Optional[str] = None
    ):
        self.session = session
        self.filepath = Path(filepath)
        self.attachments_dir = Path(attachments_dir) if attachments_dir else None
        self.attachment_index = self._index_attachments() if attachments_dir else {}

    def _index_attachments(self) -> dict[str, Path]:
        """Index attachments by datetime string, multiple possible"""
        index = {}
        for file in self.attachments_dir.iterdir():
            if not file.is_file():
                continue

            normalized = self._normalize_attachment_name(file.stem)
            if normalized in index:
                index[normalized].append(file)
            else:
                index[normalized] = [file]

        return index

    def _normalize_attachment_name(self, name: str) -> str:
        """
        Normalize an attachment filename to a comparable form:
        Example input: "November 6, 2012 at 124224 PM EST"
        Normalized: "2012-11-06 12:42:24 PM"
        """
        # Fix for non-standard chars (some exports use Unicode characters)
        name = "".join(f"\\u{ord(c):04x}" if ord(c) > 127 else c for c in name)

        pattern = r"([A-Za-z]+) (\d{1,2}), (\d{4}) at (\d{1,2})\\uf\d{3}(\d{2})\\uf\d{3}(\d{2}) (AM|PM)"
        match = re.search(pattern, name)
        if not match:
            return ""

        month_str, day, year, hour, minute, second, am_pm = match.groups()
        try:
            dt = datetime.strptime(
                f"{month_str} {day}, {year} {hour}:{minute}:{second} {am_pm}",
                "%B %d, %Y %I:%M:%S %p",
            )
            return dt.strftime("%Y-%m-%d %I:%M:%S %p")
        except ValueError:
            return ""

    def _normalize_csv_date(self, date: datetime) -> str:
        """
        Convert CSV date into the same normalized key.
        Example: "Nov 6, 2012, 12:42:24 PM" => "2012-11-06 12:42:24 PM"
        """
        try:
            return date.strftime("%Y-%m-%d %I:%M:%S %p")
        except ValueError:
            return ""

    def _guess_content_type(self, file_path: Path) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def save_media(
        self, attachment_path, message_id: str, index: int
    ) -> Optional[Media]:
        ct = self._guess_content_type(attachment_path) if attachment_path else None

        ext = os.path.splitext(attachment_path)[1]
        filename = f"{message_id}_{index}{ext}"
        filepath = MEDIA_DIR / filename

        try:
            shutil.copy2(attachment_path, filepath)
        except Exception as e:
            print(f"Failed to copy media: {e}")
            return None

        return Media(
            message_id=message_id,
            content_type=ct,
            filename=filename,
            file_path=str(filepath),
        )

    def parse(self, user_address: str):
        me = self.get_or_create_contact(user_address, "Me")
        with self.filepath.open(newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                date = datetime.strptime(row["Date"], "%b %d, %Y, %I:%M:%S %p")
                date_str = self._normalize_csv_date(date)
                contact = self.get_or_create_contact(
                    row["Phone Number"], row["Name"] if row["Name"] != "Me" else None
                )
                conversation = self.get_or_create_conversation([contact])
                direction = Direction.inbox if row["Name"] != "Me" else Direction.sent
                attachments = self.attachment_index.get(date_str, [])

                # Dedupe messages
                exists = self.session.exec(
                    select(Message).where(
                        Message.date == date,
                        Message.text == row["Message"],
                        Message.conversation_id == conversation.id,
                    )
                ).first()

                if exists:
                    continue

                message = Message(
                    date=date,
                    type=MessageType.sms if not attachments else MessageType.mms,
                    direction=direction,
                    text=row["Message"],
                    contact_id=contact.id if direction == Direction.inbox else me.id,
                    conversation_id=conversation.id,
                )

                self.session.add(message)
                self.session.commit()
                self.session.refresh(message)

                for index, attachment in enumerate(attachments):
                    media = self.save_media(attachment, message.id, index)
                    if media:
                        self.session.add(media)

        self.session.commit()
