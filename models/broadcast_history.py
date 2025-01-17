# https://scketc.sooplive.co.kr/api.php?l=DF&m=profileTheme&v=6.0&w=webk&pttype=all&isMobile=0&location=total_search&tab=total&d=이세계아이돌&order=current_sum_viewer&orderBy=desc&size=10

# https://scketc.sooplive.co.kr/api.php?l=DF&m=profileTheme&v=6.0&w=webk&pttype=all&tab=total&d=이세계아이돌

from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
import enum
from models import Base

class Status(enum.Enum):
    ON = 1
    OFF = 2

class BroadcastHistory(Base):
    
    __tablename__ = "broadcast_history"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    status = Column(Enum(Status))
    title = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    streamer_id = Column(UUID, ForeignKey("streamer.id"))
    streamer = relationship("Streamer", backref="broadcast_histories")