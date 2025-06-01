from sqlmodel import Session
from .models import SMS


def create_sms(session: Session, sms: SMS):
    session.add(sms)
    session.commit()
    session.refresh(sms)
    return sms


def get_all_sms(session: Session):
    return session.query(SMS).all()
