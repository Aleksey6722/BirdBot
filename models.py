from sqlalchemy import create_engine, String, Integer, Column, ForeignKey
from sqlalchemy.orm import Session, declarative_base, relationship
import os

USER = os.getenv('USER_DB')
PASSWORD = os.getenv('PASSWORD_DB')
engine = create_engine(f"postgresql+psycopg2://{USER}:{PASSWORD}@localhost/birdbot")
session = Session(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    chat_id = Column(Integer, nullable=False)
    bird = relationship('UserBird', backref='user')


class Bird(Base):
    __tablename__ = 'bird'
    id = Column(Integer, primary_key=True, autoincrement=True)
    common_name = Column(String(100), nullable=False, unique=True)
    scientific_name = Column(String(100), nullable=False, unique=True)
    user = relationship('UserBird', backref='bird')


class UserBird(Base):
    __tablename__ = 'userbird'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer(), ForeignKey('user.id'))
    bird_id = Column(Integer(), ForeignKey('bird.id'))


if __name__ == '__main__':
    # Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
