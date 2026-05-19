from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from . import models, schemas, crypto_engine
from .database import SessionLocal, init_db
from passlib.context import CryptContext
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    logger.info("Initializing Database...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize database: {e}")
        logger.error(traceback.format_exc())
    yield


app = FastAPI(title="Messenger API", lifespan=lifespan)


# Global error handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        body = await request.body()
        logger.error(f"Error processing request: {request.method} {request.url}")
        logger.error(f"Request body: {body.decode() if body else 'empty'}")
    except:
        pass
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check server logs for details."},
    )


# Password hashing configuration
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}


@app.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        new_user = models.User(
            username=user.username,
            password_hash=get_password_hash(user.password),
            public_key=user.public_key
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User {user.username} registered (ID: {new_user.id}).")
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error for {user.username}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{username}/public_key")
def get_public_key(username: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": username, "public_key": user.public_key}


@app.get("/users/by-id/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username, "public_key": user.public_key}


@app.post("/verify_user")
def verify_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user:
        logger.warning(f"Verification failed: User {request.username} not found.")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Verification failed: Incorrect password for {request.username}.")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.info(f"User {user.username} (ID: {user.id}) successfully verified.")
    return {"id": user.id, "username": user.username, "status": "verified"}


@app.post("/send_message")
def send_message(msg: schemas.MessageCreate, db: Session = Depends(get_db)):
    # The message is encrypted on the client side before sending
    new_msg = models.Message(
        sender_id=msg.sender_id,
        recipient_id=msg.recipient_id,
        encrypted_content=msg.encrypted_content,
        encrypted_session_key=msg.encrypted_session_key,
        encrypted_session_key_sender=msg.encrypted_session_key_sender,
        iv=msg.iv,
        integrity_hash=msg.integrity_hash,
        file_name=msg.file_name,
        file_size=msg.file_size
    )
    db.add(new_msg)
    db.commit()
    logger.info(f"Message from {msg.sender_id} to {msg.recipient_id} stored. Server cannot read the content.")
    return {"status": "Message sent and stored encrypted."}


@app.get("/messages/{user_id}")
def get_messages(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import or_
    messages = db.query(models.Message).filter(
        or_(models.Message.recipient_id == user_id, models.Message.sender_id == user_id)
    ).order_by(models.Message.sent_at.asc()).all()
    return messages
