"""
Database Models
SQLAlchemy models for user data and listening history
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    user_id = Column(String(255), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    profile = Column(JSON, default=dict)  # User preferences and settings
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    listening_history = relationship("ListeningHistory", back_populates="user", cascade="all, delete-orphan")
    user_songs = relationship("UserSong", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """User session model"""
    __tablename__ = "sessions"
    
    token = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class Song(Base):
    """Song model - stores song metadata"""
    __tablename__ = "songs"
    
    song_id = Column(String(255), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    artists = Column(JSON, nullable=False)  # List of artist names
    genre = Column(JSON, default=list)  # List of genres
    album = Column(String(500), nullable=True)
    image = Column(Text, nullable=True)
    platform = Column(String(50), default="unknown")
    platform_id = Column(String(255), nullable=True)
    youtube_video_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    extra_data = Column(JSON, default=dict)  # Additional metadata
    
    # Relationships
    user_songs = relationship("UserSong", back_populates="song", cascade="all, delete-orphan")
    listening_history = relationship("ListeningHistory", back_populates="song")


class UserSong(Base):
    """User's song collection - links users to songs"""
    __tablename__ = "user_songs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    song_id = Column(String(255), ForeignKey("songs.song_id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), default="manual")  # manual, recommendation, search, etc.
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_favorite = Column(Boolean, default=False)
    play_count = Column(Integer, default=0)
    last_played = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_songs")
    song = relationship("Song", back_populates="user_songs")


class ListeningHistory(Base):
    """Listening history - tracks when users listen to songs"""
    __tablename__ = "listening_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    song_id = Column(String(255), ForeignKey("songs.song_id", ondelete="CASCADE"), nullable=True, index=True)
    song_title = Column(String(500), nullable=False)  # Store title even if song is deleted
    artists = Column(JSON, nullable=False)  # Store artists even if song is deleted
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String(50), default="recommendation")  # recommendation, search, etc.
    platform = Column(String(50), nullable=True)
    duration_seconds = Column(Float, nullable=True)  # How long they listened
    completed = Column(Boolean, default=False)  # Did they listen to the full song?
    extra_data = Column(JSON, default=dict)  # Additional metadata
    
    # Relationships
    user = relationship("User", back_populates="listening_history")
    song = relationship("Song", back_populates="listening_history")


class TasteProfile(Base):
    """User taste profile for recommendations"""
    __tablename__ = "taste_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    profile_data = Column(JSON, nullable=False)  # Taste vector, preferences, etc.
    song_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Database setup
def get_database_url():
    """
    Get database URL from environment.
    Supports PostgreSQL (for production) and SQLite (for development).
    
    Environment variables:
    - DATABASE_URL: Full database connection string (postgresql://user:pass@host:port/dbname)
    - DB_HOST: PostgreSQL host (default: localhost)
    - DB_PORT: PostgreSQL port (default: 5432)
    - DB_NAME: Database name (default: aura_music)
    - DB_USER: Database user (default: postgres)
    - DB_PASSWORD: Database password (required for PostgreSQL)
    
    For PostgreSQL: postgresql://user:password@host:port/dbname
    For SQLite (fallback): sqlite:///data/aura.db
    """
    # Check for full DATABASE_URL first (used by most hosting providers)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Some providers use postgres:// instead of postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    # Build PostgreSQL URL from individual components
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aura_music")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD")
    
    # If password is provided, use PostgreSQL
    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback to SQLite for local development
    print("⚠ No PostgreSQL credentials found. Using SQLite for local development.")
    print("   Set DATABASE_URL or DB_PASSWORD environment variable to use PostgreSQL.")
    data_dir = os.getenv("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(data_dir, 'aura.db')}"


def create_engine_instance():
    """Create SQLAlchemy engine"""
    database_url = get_database_url()
    
    # SQLite specific settings
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},  # Needed for SQLite
            echo=False  # Set to True for SQL query logging
        )
    else:
        # PostgreSQL settings
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Max overflow connections
            echo=False  # Set to True for SQL query logging
        )
    
    return engine


def get_session_local():
    """Get database session factory"""
    engine = create_engine_instance()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create engine and session factory
engine = create_engine_instance()
SessionLocal = get_session_local()


def init_database():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

