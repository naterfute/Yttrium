
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, Sequence, TIMESTAMP, Boolean, Enum, select, ForeignKey, update
from sqlalchemy.sql import func

Base = declarative_base()


class Requests(Base):
    """Table for Storing Download Requests"""
    __tablename__ = 'requests'
    id = Column(Integer, autoincrement=True, primary_key=True)
    title = Column(String, default=None)
    url = Column(String, unique=True)
    extractor = Column(String(100))
    queue_status = Column(
        Enum('queued', 'completed', name='queue_status'), default='queued')
    create_time = Column(TIMESTAMP, default=func.now())
    download_time = Column(TIMESTAMP, default=None)
    downloaded_items = relationship(
        'Downloaded', back_populates='playlist')


class Downloaded(Base):
    """Table for Storing Downloaded videos"""
    __tablename__ = 'downloaded'
    id = Column(Integer, autoincrement=True, primary_key=True)
    title = Column(String)
    url = Column(String)
    playlist_url = Column(String, ForeignKey('requests.url'))
    path = Column(String)
    elapsed = Column(String)
    create_time = Column(TIMESTAMP, default=func.now())
    download_time = Column(TIMESTAMP, default=None)
    playlist = relationship('Requests', back_populates='downloaded_items')


class Users(Base):
    """Table for Storing User Accounts and info"""
    __tablename__ = "users"
    id = Column(Integer, autoincrement=True, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(500))
    salt = Column(String(100))
    admin = Column(Boolean(False), default=False)

class Authors(Base):
    """Table for Storing Known Channels and the path they are located at"""
    __tablename__ = "Authors"
    id = Column(Integer, autoincrement=True, primary_key=True)
    author = Column(String, unique=True)
    path = Column(String, unique=False)


