"""
Fixtures partagées pour les tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import os
from datetime import datetime

from app.main import app
from app.core.database import Base, get_db_session, db_manager
from app.models.user import User
from app.models.listing import Listing
from app.core.auth import create_access_token, get_password_hash

# Base de données de test (SQLite en mémoire)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Moteur de test
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fixture pour une session DB de test avec rollback automatique."""
    # Création des tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Session de test
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()
    
    # Nettoyage après test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Fixture pour le client HTTP de test."""
    
    # Override de la dépendance get_db_session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    # Client de test asynchrone
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Nettoyage
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Fixture pour un utilisateur de test."""
    user = User(
        phone="+261321234567",
        full_name="Test User",
        role="agriculteur",
        region="Analamanga",
        account_type="physical",
        hashed_password=get_password_hash("Test123!"),
        verification_status="verified"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
async def test_listing(db_session: AsyncSession, test_user: User) -> Listing:
    """Fixture pour une annonce de test."""
    listing = Listing(
        user_id=test_user.id,
        product="Riz",
        description="Riz de première qualité",
        total_quantity=100.00,
        available_quantity=100.00,
        unit="kg",
        price=1500.00,
        price_mode="without_delivery",
        region="Analamanga",
        is_in_season=True,
        status="available"
    )
    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)
    return listing

@pytest.fixture(scope="function")
def user_token(test_user: User) -> str:
    """Fixture pour un token JWT de test."""
    return create_access_token(
        data={"sub": str(test_user.id), "phone": test_user.phone, "role": test_user.role}
    )

@pytest.fixture(scope="function")
def auth_headers(user_token: str) -> dict:
    """Fixture pour les headers d'authentification."""
    return {"Authorization": f"Bearer {user_token}"}
