from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from models import Base
import enum

class PostType(enum.Enum):
    Cafe = 0
    Soop = 1
    Instagram = 2
    X = 3

class Post(Base):
    
    __tablename__ = "post"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    type = Column(Enum(PostType))
    uploaded_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    streamer_id = Column(UUID, ForeignKey("streamer.id"))
    streamer = relationship("Streamer", backref="post", foreign_keys=[streamer_id])
    
    cafe_post_id = Column(UUID, ForeignKey("cafe_post.id"))
    cafe_post = relationship("CafePost", backref="post", foreign_keys=[cafe_post_id])
    
    x_post_id = Column(UUID, ForeignKey("x_post.id"))
    x_post = relationship("XPost", backref="post", foreign_keys=[x_post_id])
    
    ig_post_id = Column(UUID, ForeignKey("ig_post.id"))
    ig_post = relationship("IgPost", backref="post", foreign_keys=[ig_post_id])
    
    soop_post_id = Column(UUID, ForeignKey("soop_post.id"))
    soop_post = relationship("SoopPost", backref="post", foreign_keys=[soop_post_id])
    
    yt_post_id = Column(UUID, ForeignKey("yt_post.id"))
    yt_post = relationship("YtPost", backref="post", foreign_keys=[yt_post_id])