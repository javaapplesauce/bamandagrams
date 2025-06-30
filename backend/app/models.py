# backend/app/models.py
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column, Session
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text
import os
from typing import Optional, List
import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

# Async SQLAlchemy setup
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

# ORM Models
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    matches: Mapped[List["MatchPlayer"]] = relationship("MatchPlayer", back_populates="user")

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # lobby code used
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    # Relationships
    players: Mapped[List["MatchPlayer"]] = relationship("MatchPlayer", back_populates="match", cascade="all, delete-orphan")
    words: Mapped[List["WordPlayed"]] = relationship("WordPlayed", back_populates="match", cascade="all, delete-orphan")

class MatchPlayer(Base):
    __tablename__ = "match_players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(50))  # player name used in the game
    score: Mapped[int] = mapped_column(Integer)
    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="players")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="matches")
    words: Mapped[List["WordPlayed"]] = relationship("WordPlayed", back_populates="player", cascade="all, delete-orphan")

class WordPlayed(Base):
    __tablename__ = "words_played"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    player_id: Mapped[int] = mapped_column(ForeignKey("match_players.id", ondelete="CASCADE"))
    word: Mapped[str] = mapped_column(String(32))
    points: Mapped[int] = mapped_column(Integer)
    was_stolen: Mapped[bool] = mapped_column(nullable=False, default=False)  # indicate if this word was a result of a steal
    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="words")
    player: Mapped["MatchPlayer"] = relationship("MatchPlayer", back_populates="words")
