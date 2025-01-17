from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from models import Base

class CafePost(Base):
    
    __tablename__ = "cafe_post"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(String, unique=True)
    
    url = Column(String)
    category = Column(String)
    title = Column(String)
    content = Column(String)
    uploaded_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    streamer_id = Column(UUID, ForeignKey("streamer.id"))
    streamer = relationship("Streamer", backref="cafe_posts")