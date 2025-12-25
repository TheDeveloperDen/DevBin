from sqlalchemy import TIMESTAMP, UUID, Boolean, Column, Integer, String, func, text

from app.db.base import Base

UUID_DEFAULT = text("gen_random_uuid()")


class PasteEntity(Base):
    __tablename__ = "pastes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    title = Column(String(255), nullable=False)
    content_path = Column(String, nullable=False)
    content_language = Column(String, nullable=False, server_default="plain_text")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    content_size = Column(Integer, nullable=False)
    is_compressed = Column(Boolean, nullable=False, server_default='false')
    original_size = Column(Integer, nullable=True)

    creator_ip = Column(String)
    creator_user_agent = Column(String)

    edit_token = Column(String)
    last_updated_at = Column(TIMESTAMP(timezone=True))

    delete_token = Column(String)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Paste(id={self.id}, title='{self.title}')>"

    def __str__(self):
        return self.title
