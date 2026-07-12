# script to connect to database
import config

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def initialize():
    engine = create_engine(config.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    return engine, SessionLocal, Base

