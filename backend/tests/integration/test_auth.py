"""
Tests d'intégration pour l'authentification.
"""
import pytest
from httpx import AsyncClient
from app.core.auth import create_access_token

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session):
    """Test d'inscription d'un utilisateur."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": "+261321234568",
            "full_name": "Marie Rakoto",
            "role": "agriculteur",
            "region": "Analamanga",
            "account_type": "physical",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == "+261321234568"
    assert data["full_name"] == "Marie Rakoto"
    assert "id" in data
    assert "hashed_password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_phone(client: AsyncClient, test_user):
    """Test d'inscription avec un téléphone déjà existant."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "phone": "+261321234567",  # Téléphone de test_user
            "full_name": "Duplicate User",
            "role": "agriculteur",
            "region": "Analamanga",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 409
    assert "déjà enregistré" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test de connexion réussie."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "+261321234567",
            "password": "Test123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["phone"] == "+261321234567"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test de connexion avec mot de passe incorrect."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "+261321234567",
            "password": "WrongPassword"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test de connexion avec un utilisateur inexistant."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "+261321234569",
            "password": "Test123!"
        }
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers):
    """Test de récupération de l'utilisateur courant."""
    # Création d'un endpoint de test pour récupérer l'utilisateur
    from app.api.v1 import auth
    
    # On va plutôt tester via un endpoint protégé existant
    # Par exemple, la création d'une annonce
    
    response = await client.post(
        "/api/v1/listings/",
        headers=auth_headers,
        json={
            "product": "Riz",
            "total_quantity": 100,
            "unit": "kg",
            "price": 1500,
            "region": "Analamanga"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["product"] == "Riz"
    assert "user_id" in data
