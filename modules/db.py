from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from models.models import Base
import models.models as Models

class DB:
    
    __slots__ = (
        "session",
    )
    
    def __init__(self) -> None:
        SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL")

        engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
        Session = sessionmaker(engine)
        self.session = Session()

        # Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)