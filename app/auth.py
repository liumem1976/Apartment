from datetime import datetime, timedelta
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from .db import engine
from .models import User

SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Cookie/session settings
SESSION_COOKIE_NAME = "ap_session"
SESSION_EXPIRE_SECONDS = 60 * 60 * 12


def _sign_session(payload: str) -> str:
    """Sign a session payload using HMAC-SHA256 and SECRET_KEY.

    Format: payload|hexsig
    """
    import hashlib
    import hmac

    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def _unsign_session(token: str) -> Optional[str]:
    import hashlib
    import hmac

    try:
        payload, sig = token.rsplit("|", 1)
    except Exception:
        return None
    expected = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return payload


def create_session_cookie(user: User) -> str:
    """Create a signed session token for the given user.

    The payload contains: user_id:issued_at
    """
    import time

    payload = f"{user.id}:{int(time.time())}"
    return _sign_session(payload)


def parse_session_cookie(token: str) -> Optional[int]:
    """Return user_id if token valid and not expired, else None."""
    import time

    payload = _unsign_session(token)
    if not payload:
        return None
    try:
        user_id_s, issued_s = payload.split(":", 1)
        issued = int(issued_s)
        if int(time.time()) - issued > SESSION_EXPIRE_SECONDS:
            return None
        return int(user_id_s)
    except Exception:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(username: str, password: str) -> Optional[User]:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise credentials_exception
        return user


def require_role(role: str):
    def _role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user

    return _role_checker


def get_current_user_from_cookie(request: Request) -> Optional[User]:
    """Dependency to extract user from signed cookie (for HTML routes).

    Returns User or raises HTTPException(401).
    """
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = parse_session_cookie(cookie)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    with Session(engine) as session:
        # Avoid selecting columns that may be missing in older DBs; select core
        # fields and construct a lightweight User-like object so tests and
        # older DBs without `is_active` still work.
        from sqlmodel import select as _select

        row = session.exec(
            _select(User.id, User.username, User.password_hash, User.role).where(
                User.id == user_id
            )
        ).first()
        if not row:
            raise HTTPException(status_code=401, detail="User inactive or not found")
        u = User(id=row[0], username=row[1], password_hash=row[2], role=row[3])
        # default to active when DB column is absent
        if not hasattr(u, "is_active"):
            setattr(u, "is_active", True)
        return u


def require_any_role(*roles: str):
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == "admin":
            return current_user
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user

    return _checker


def require_role_cookie(role: str):
    """Role checker for cookie-based HTML routes."""

    def _checker(current_user: User = Depends(get_current_user_from_cookie)) -> User:
        if current_user.role != role and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return current_user

    return _checker
