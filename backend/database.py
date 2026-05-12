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
        # Add column if not exists (SQLite specific check)
        with engine.connect() as conn:
            from sqlalchemy import text
            try:
                conn.execute(text("ALTER TABLE messages ADD COLUMN encrypted_session_key_sender TEXT"))
                conn.commit()
            except:
                pass # Already exists or table not ready
    except Exception as e:
        import logging
        logging.getLogger("API").error(f"init_db failed: {e}")
        raise e
