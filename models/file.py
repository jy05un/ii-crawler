from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from models import Base
import enum

class FileType(enum.Enum):
    local = 0
    external = 1

class File(Base):
    
    __tablename__ = "file"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    name = Column(String)
    mime_type = Column(String)
    size = Column(Integer)
    url = Column(String)
    file_type = Column(Enum(FileType))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    post_id = Column(UUID, ForeignKey("post.id"))
    post = relationship("Post", backref="files", foreign_keys=[post_id])
    
    # cafe_post_id = Column(UUID, ForeignKey("cafe_post.id"))
    # cafe_post = relationship("CafePost", backref="files", foreign_keys=[cafe_post_id])
    
    # x_post_id = Column(UUID, ForeignKey("x_post.id"))
    # x_post = relationship("XPost", backref="files", foreign_keys=[x_post_id])
    
    # ig_post_id = Column(UUID, ForeignKey("ig_post.id"))
    # ig_post = relationship("IgPost", backref="files", foreign_keys=[ig_post_id])
    
    # soop_post_id = Column(UUID, ForeignKey("soop_post.id"))
    # soop_post = relationship("SoopPost", backref="files", foreign_keys=[soop_post_id])
    
    # yt_post_id = Column(UUID, ForeignKey("yt_post.id"))
    # yt_post = relationship("YtPost", backref="files", foreign_keys=[yt_post_id])