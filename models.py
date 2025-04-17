from sqlalchemy import Column, Integer, String, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)

class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), index=True)
    start_time = Column(String(50))  # Add length here
    end_time = Column(String(50))    # Add length here
    label = Column(String(100))
    type = Column(String(50))        # 'event' or 'intervention'
    description = Column(Text)
