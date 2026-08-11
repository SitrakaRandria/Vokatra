"""
Tests d'intégration pour les endpoints de listings.
"""
import pytest
from httpx import AsyncClient
from app.models.listing import Listing

@pytest.mark.asyncio
async def test_create_listing(client: AsyncClient, auth_headers):
    """Test de création d'une annonce."""
    response = await client.post(
        "/api/v1/listings/",
        headers=auth_headers,
        json={
            "product": "Manioc",
            "description": "Manioc frais de saison",
            "total_quantity": 50.00,
            "unit": "kg",
            "price": 800.00,
            "price_mode": "without_delivery",
            "region": "Analamanga",
            "location_detail": "Antananarivo"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["product"] == "Manioc"
    assert data["available_quantity"] == 50.00
    assert data["status"] == "available"
    assert "is_in_season" in data

@pytest.mark.asyncio
async def test_get_listings(client: AsyncClient, test_listing):
    """Test de récupération des annonces."""
    response = await client.get("/api/v1/listings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(l["id"] == test_listing.id for l in data)

@pytest.mark.asyncio
async def test_get_listings_with_filters(client: AsyncClient, test_listing):
    """Test de récupération avec filtres."""
    response = await client.get(
        "/api/v1/listings/",
        params={
            "product": "Riz",
            "region": "Analamanga",
            "min_price": 1000
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert all(l["product"] == "Riz" for l in data)
    assert all(l["region"] == "Analamanga" for l in data)

@pytest.mark.asyncio
async def test_get_listing_by_id(client: AsyncClient, test_listing):
    """Test de récupération d'une annonce par ID."""
    response = await client.get(f"/api/v1/listings/{test_listing.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_listing.id
    assert data["product"] == test_listing.product

@pytest.mark.asyncio
async def test_update_listing(client: AsyncClient, auth_headers, test_listing):
    """Test de mise à jour d'une annonce."""
    response = await client.put(
        f"/api/v1/listings/{test_listing.id}",
        headers=auth_headers,
        json={
            "price": 1600.00,
            "description": "Nouvelle description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 1600.00
    assert data["description"] == "Nouvelle description"

@pytest.mark.asyncio
async def test_delete_listing(client: AsyncClient, auth_headers, test_listing):
    """Test de suppression d'une annonce."""
    response = await client.delete(
        f"/api/v1/listings/{test_listing.id}",
        headers=auth_headers
    )
    assert response.status_code == 204
    
    # Vérification que l'annonce a bien été supprimée
    response = await client.get(f"/api/v1/listings/{test_listing.id}")
    assert response.status_code == 404
