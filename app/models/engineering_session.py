"""Persistent server-side sessions for MIDRA Engineering."""
from datetime import datetime
from sqlalchemy import DateTime,String
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base

class EngineeringSession(Base):
    __tablename__="engineering_sessions"
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_email: Mapped[str]=mapped_column(String(320),nullable=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,index=True)
