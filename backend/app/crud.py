# backend/app/crud.py
from sqlalchemy.future import select
from passlib.context import CryptContext
from . import models, schemas
import datetime
from typing import Optional
from typing import List
from typing import Dict
from fastapi import HTTPException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# User CRUD
async def get_user_by_username(session: models.AsyncSession, username: str) -> Optional[models.User]:
    result = await session.execute(select(models.User).where(models.User.username == username))
    return result.scalars().first()

async def create_user(session: models.AsyncSession, user_in: schemas.UserCreate) -> models.User:
    user = models.User(username=user_in.username, email=user_in.email or None,
                       password_hash=hash_password(user_in.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

# Save match results after game end
async def save_match_results(session: models.AsyncSession, game: "GameState", results: List[Dict]) -> models.Match:
    # Create Match record
    match = models.Match(code=game.code, ended_at=datetime.utcnow())
    session.add(match)
    # For each player result, create a MatchPlayer and WordPlayed records
    for res in results:
        name = res["name"]
        score = res["score"]
        # If the player was a registered user (we could map by name to user if logged in, but here we didn't attach user_id in GameState)
        mp = models.MatchPlayer(match=match, name=name, score=score)
        session.add(mp)
        # Also record each word that player had at end
        player_state = game.players  # game is GameState, which lacks direct user_id mapping in this MVP
        # We won't have word details here easily; for MVP, skip logging individual words or implement as needed.
    await session.commit()
    await session.refresh(match)
    return match

# Dependency for getting current user from JWT for /auth/me
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, models.JWT_SECRET, algorithms=[models.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    async with models.SessionLocal() as session:
        result = await session.execute(select(models.User).where(models.User.id == int(user_id)))
        user = result.scalars().first()
        if not user:
            raise credentials_exception
        return user
