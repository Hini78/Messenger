from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./corporate_chat.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    try:
        from . import models
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.getLogger("API").error(f"init_db failed: {e}")
        raise e
