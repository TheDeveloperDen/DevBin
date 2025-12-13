import uuid

from sqlalchemy import UUID, Column, DateTime, Integer, String, func, text

from app.db.base import Base

UUID_DEFAULT = text("gen_random_uuid()")


class PasteEntity(Base):
    __tablename__ = "pastes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    title = Column(String(255), nullable=False)
    content_path = Column(String, nullable=False)
    content_language = Column(String, nullable=False, server_default="plain_text")
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    content_size = Column(Integer, nullable=False)

    creator_ip = Column(String)
    creator_user_agent = Column(String)

    def __repr__(self):
        return f"<Paste(id={self.id}, title='{self.title}')>"

    def __str__(self):
        return self.title
