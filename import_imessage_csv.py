# cli.py

import sys
from sqlmodel import SQLModel, Session, create_engine
from app.parser import CSV
from typing import Optional

sqlite_url = "sqlite:///sms.db"
engine = create_engine(sqlite_url)


def ingest_csv(filepath: str, user_address: str, attachments_dir: Optional[str] = None):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        importer = CSV(session, filepath, attachments_dir)
        importer.parse(user_address)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python cli.py path/to/file.csv user_number attachments_dir")
        sys.exit(1)

    filepath = sys.argv[1]
    user_address = sys.argv[2] if len(sys.argv) > 2 else None
    ingest_csv(filepath, user_address, sys.argv[3])
