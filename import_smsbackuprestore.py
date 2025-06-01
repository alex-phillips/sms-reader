# cli.py

import sys
from sqlmodel import SQLModel, Session, create_engine
from app.parser import SMSBackupAndRestore

sqlite_url = "sqlite:////data/sms.db"
engine = create_engine(sqlite_url)


def ingest_large_xml(filepath: str, user_address: str):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        importer = SMSBackupAndRestore(session)
        importer.parse_sms_xml_stream(filepath, user_address)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python cli.py path/to/file.xml user_number")
        sys.exit(1)

    filepath = sys.argv[1]
    user_address = sys.argv[2] if len(sys.argv) > 2 else None
    ingest_large_xml(filepath, user_address)
