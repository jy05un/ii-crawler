from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
import enum
from models import Base

class ChatType(enum.Enum):

    text = 1
    img = 2

class ChatRecord(Base):
    
    __tablename__ = "chat_record"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    url = Column(String)
    chat_type = Column(Enum(ChatType))
    sent_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    streamer_id = Column(UUID, ForeignKey("streamer.id"))
    streamer = relationship("Streamer", backref="chat_records")