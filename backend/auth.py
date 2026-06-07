"""
Authentication utilities and SQLAlchemy user model for ChatAgent.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Generator, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, DateTime, String, Text, create_engine, func, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.database import DATA_DIR

SECRET_KEY = os.getenv("AUTH_SECRET_KEY") or os.getenv("SECRET_KEY") or "please-change-this-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'auth.db'}"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


def init_auth_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if str(engine.url).startswith("sqlite"):
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "updated_at" not in columns:
                with engine.begin() as connection:
                    connection.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def create_user(db: Session, full_name: str, email: str, password: str) -> User:
    user = User(
        full_name=full_name.strip(),
        email=email.lower().strip(),
        password_hash=get_password_hash(password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise ValueError("A user with that email already exists.")


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expires = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expires, "sub": payload.get("sub")})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        if email is None and user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    if user_id:
        user = db.query(User).filter(User.id == str(user_id)).first()
    else:
        user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user


# Ensure auth database is always initialized when the module is imported.
init_auth_db()
