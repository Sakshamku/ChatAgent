"""
Authentication utilities and SQLAlchemy user model for ChatAgent.
"""
import hashlib
import os
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Generator, Optional

import bcrypt
import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, model_validator
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Column, DateTime, String, Text, ForeignKey, create_engine, func, inspect, text, UniqueConstraint
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


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_api_keys_user_provider"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    encrypted_api_key = Column(Text, nullable=False)
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
    confirm_password: str

    @model_validator(mode="after")
    def validate_passwords(self) -> "SignupRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


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


class ApiKeyUpsertRequest(BaseModel):
    provider: str = "mistral"
    api_key: str


class ApiKeyStatusResponse(BaseModel):
    has_key: bool
    provider: Optional[str] = None
    masked_api_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApiKeyValidationResponse(BaseModel):
    valid: bool
    message: Optional[str] = None


def _derive_fernet_key() -> bytes:
    configured_key = os.getenv("ENCRYPTION_KEY")
    if configured_key:
        return configured_key.encode("utf-8")

    fallback_key = os.getenv("SECRET_KEY") or "chatagent-default-secret"
    digest = hashlib.sha256(fallback_key.encode("utf-8")).digest()
    return urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    try:
        return Fernet(_derive_fernet_key())
    except Exception as exc:
        raise RuntimeError("ENCRYPTION_KEY is invalid") from exc


def encrypt_api_key(api_key: str) -> str:
    return get_fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return get_fernet().decrypt(encrypted_api_key.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt API key") from exc


def mask_api_key(api_key: str) -> str:
    api_key = api_key.strip()
    if len(api_key) <= 4:
        return "*" * max(4, len(api_key))
    return f"{'*' * max(8, len(api_key) - 4)}{api_key[-4:]}"


def get_user_api_key(db: Session, user_id: str, provider: str = "mistral") -> Optional[ApiKey]:
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user_id, ApiKey.provider == provider.lower().strip())
        .first()
    )


def get_user_api_key_status(db: Session, user_id: str, provider: str = "mistral") -> ApiKeyStatusResponse:
    record = get_user_api_key(db, user_id, provider)
    if not record:
        return ApiKeyStatusResponse(has_key=False, provider=provider.lower().strip())
    try:
        decrypted = decrypt_api_key(record.encrypted_api_key)
    except Exception:
        return ApiKeyStatusResponse(has_key=False, provider=provider.lower().strip())
    return ApiKeyStatusResponse(
        has_key=True,
        provider=record.provider,
        masked_api_key=mask_api_key(decrypted),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def save_user_api_key(db: Session, user_id: str, provider: str, api_key: str) -> ApiKey:
    provider = provider.lower().strip()
    encrypted = encrypt_api_key(api_key.strip())
    record = get_user_api_key(db, user_id, provider)
    if record:
        record.encrypted_api_key = encrypted
        db.add(record)
    else:
        record = ApiKey(
            user_id=user_id,
            provider=provider,
            encrypted_api_key=encrypted,
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_user_api_key(db: Session, user_id: str, provider: str = "mistral") -> bool:
    record = get_user_api_key(db, user_id, provider)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def validate_mistral_api_key(api_key: str) -> tuple[bool, str]:
    api_key = api_key.strip()
    if not api_key:
        return False, "Invalid API Key"
    try:
        response = requests.get(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if response.ok:
            return True, "Valid API Key"
        return False, "Invalid API Key"
    except Exception:
        return False, "Invalid API Key"


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
