"""Authentication endpoints: register, login, current user."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..dependencies import USER_COLUMNS, CurrentUser, DbConnection
from ..schemas import Token, UserPublic, UserRegister
from ..security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

DUPLICATE_USER = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Username or email is already registered",
)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: DbConnection):
    """Create a new account. New players start at 1000 Elo (Bronze)."""
    email = data.email.lower()

    existing = db.execute(
        text("SELECT id FROM users WHERE username = :username OR email = :email"),
        {"username": data.username, "email": email},
    ).first()
    if existing is not None:
        raise DUPLICATE_USER

    try:
        result = db.execute(
            text("INSERT INTO users (username, email, password_hash) "
                 "VALUES (:username, :email, :password_hash)"),
            {"username": data.username, "email": email,
             "password_hash": hash_password(data.password)},
        )
        db.commit()
    except IntegrityError:  # two people registered the same name at the same moment
        db.rollback()
        raise DUPLICATE_USER from None

    row = db.execute(
        text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
        {"id": result.lastrowid},
    ).mappings().one()
    return dict(row)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbConnection):
    """Log in with username (or email) and password. Returns a bearer token."""
    row = db.execute(
        text("SELECT id, password_hash FROM users "
             "WHERE username = :login OR email = :login_email"),
        {"login": form.username, "login_email": form.username.lower()},
    ).first()

    if row is None:
        verify_password(form.password, DUMMY_HASH)  # same timing as a real check
        password_ok = False
    else:
        password_ok = verify_password(form.password, row.password_hash)

    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(row.id))


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: CurrentUser):
    """Return the logged-in user's account (requires a token)."""
    return current_user