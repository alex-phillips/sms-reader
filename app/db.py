from sqlmodel import SQLModel, Session, create_engine

sqlite_file_name = "sms.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}", echo=False)


def get_session():
    with Session(engine) as session:
        yield session
