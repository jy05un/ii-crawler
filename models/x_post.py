from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4
from models import Base
import enum

class RefType(enum.Enum):
    Retweeted = 0
    Quoted = 1
    Replied_to = 2

class XPost(Base):
    
    __tablename__ = "x_post"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(String, unique=True)
    
    url = Column(String)
    content = Column(String)
    uploaded_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # streamer_id = Column(UUID, ForeignKey("streamer.id"))
    # streamer = relationship("Streamer", backref="x_posts")
    
    ref_profile_json = Column(MutableDict.as_mutable(JSONB))
    ref_type = Column(Enum(RefType))
    
    