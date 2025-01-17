from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from models import Base

class Streamer(Base):
    
    __tablename__ = "streamer"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, unique=True)
    
    # soop_name = Column(String)
    # soop_id = Column(String)
    
    # x_name = Column(String)
    # x_id = Column(String)
    
    # ig_name = Column(String)
    # ig_id = Column(String)
    
    # cafe_name = Column(String)
    # cafe_id = Column(String)
    
    # yt_main_name = Column(String)
    # yt_main_id = Column(String)
    
    # yt_sub_name = Column(String)
    # yt_sub_id = Column(String)
    
    # yt_vod_name = Column(String)
    # yt_vod_id = Column(String)
    
    # yt_wakta_name = Column(String)
    # yt_wakta_id = Column(String)
    
    # wakscord_id = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())