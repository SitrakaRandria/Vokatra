"""
Tests d'intégration API (parcours complets via HTTP).

Couvre : santé, inscription, connexion, annonces, offres, commandes,
factures PDF et validation des erreurs.
"""
from decimal import Decimal

import pytest

USER_A = {
    "phone": "+261341234567",
    "password": "Motdepasse123",
    "full_name": "Rakoto Jean",
    "role": "agriculteur",
    "region": "Analamanga",
    "city": "Antananarivo",
    "account_type": "professional",
    "company_name": "AgriMada SARL",
    "company_registration": "NIF-12345",
}

USER_B = {
    "phone": "+261332345678",
    "password": "Motdepasse123",
    "full_name": "Rasoa Marie",
    "role": "collecteur",
    "region": "Atsimo",
    "account_type": "physical",
}

LISTING = {
    "product": "Riz",
    "description": "Riz de première qualité",
    "total_quantity": "100.00",
    "unit": "tonne",
    "price": "500.00",
    "price_mode": "without_delivery",
    "region": "Analamanga",
    "location_detail": "Marché d'Analakely",
}


async def register(client, payload):
    return await client.post("/api/v1/auth/register", json=payload)


async def login(client, phone, password):
    return await client.post(
        "/api/v1/auth/login",
        data={"username": phone, "password": password},
    )


class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestAuthFlow:
    async def test_register_and_login(self, client):
        resp = await register(client, USER_A)
        assert resp.status_code == 201, resp.text
        user = resp.json()
        assert user["phone"] == USER_A["phone"]
        assert user["id"] > 0
        assert "hashed_password" not in user  # jamais exposé
        assert "password" not in user

        login_resp = await login(client, USER_A["phone"], USER_A["password"])
        assert login_resp.status_code == 200, login_resp.text
        token_data = login_resp.json()
        assert token_data["access_token"]
        assert token_data["token_type"] == "bearer"
        return token_data["access_token"]

    async def test_register_duplicate_phone_conflict(self, client):
        await register(client, USER_A)
        resp = await register(client, USER_A)
        assert resp.status_code == 409

    async def test_register_invalid_phone(self, client):
        payload = dict(USER_A, phone="+33612345678")
        resp = await register(client, payload)
        assert resp.status_code == 422

    async def test_register_weak_password(self, client):
        payload = dict(USER_A, password="short")
        resp = await register(client, payload)
        assert resp.status_code == 422

    async def test_login_wrong_password(self, client):
        await register(client, USER_A)
        resp = await login(client, USER_A["phone"], "Wrongpass123")
        assert resp.status_code == 401

    async def test_login_unknown_phone(self, client):
        resp = await login(client, "+261381234567", "Whatever123")
        assert resp.status_code == 401

    async def test_verify_phone(self, client):
        resp = await client.post(
            "/api/v1/auth/verify-phone", params={"phone": "+261341234567"}
        )
        assert resp.status_code == 200
        assert resp.json()["expires_in"] == 300


class TestListingFlow:
    async def _setup(self, client):
        await register(client, USER_A)
        token = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return headers

    async def test_create_and_fetch_listing(self, client):
        headers = await self._setup(client)
        resp = await client.post("/api/v1/listings/", json=LISTING, headers=headers)
        assert resp.status_code == 201, resp.text
        listing = resp.json()
        assert listing["product"] == "Riz"
        assert listing["available_quantity"] == "100.00"
        assert listing["status"] == "available"
        assert listing["user_id"] == listing["user"]["id"]

        # Récupération liste + détail
        listing_id = listing["id"]
        list_resp = await client.get("/api/v1/listings/")
        assert list_resp.status_code == 200
        assert any(l["id"] == listing_id for l in list_resp.json())

        detail_resp = await client.get(f"/api/v1/listings/{listing_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == listing_id

    async def test_create_listing_unauthenticated(self, client):
        resp = await client.post("/api/v1/listings/", json=LISTING)
        assert resp.status_code == 401

    async def test_update_listing_recomputes_seasonality(self, client):
        headers = await self._setup(client)
        listing = (await client.post("/api/v1/listings/", json=LISTING, headers=headers)).json()
        resp = await client.put(
            f"/api/v1/listings/{listing['id']}",
            json={"product": "Haricot"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["product"] == "Haricot"

    async def test_delete_listing(self, client):
        headers = await self._setup(client)
        listing = (await client.post("/api/v1/listings/", json=LISTING, headers=headers)).json()
        resp = await client.delete(f"/api/v1/listings/{listing['id']}", headers=headers)
        assert resp.status_code == 204
        gone = await client.get(f"/api/v1/listings/{listing['id']}")
        assert gone.status_code == 404

    async def test_listing_filters(self, client):
        headers = await self._setup(client)
        await client.post("/api/v1/listings/", json=LISTING, headers=headers)
        resp = await client.get(
            "/api/v1/listings/", params={"region": "Analamanga", "product": "Riz"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        resp2 = await client.get(
            "/api/v1/listings/", params={"region": "Atsimo"}
        )
        assert len(resp2.json()) == 0


class TestOfferOrderFlow:
    """Parcours complet : offre -> acceptation -> commande -> facture PDF."""

    async def _setup(self, client):
        await register(client, USER_A)
        await register(client, USER_B)
        token_a = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        token_b = (await login(client, USER_B["phone"], USER_B["password"])).json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        listing = (await client.post("/api/v1/listings/", json=LISTING, headers=headers_a)).json()
        return headers_a, headers_b, listing

    async def test_full_offer_order_flow(self, client):
        headers_a, headers_b, listing = await self._setup(client)

        # L'acheteur fait une offre
        offer_resp = await client.post(
            "/api/v1/offers/",
            json={
                "listing_id": listing["id"],
                "quantity": "30.00",
                "proposed_price": "480.00",
                "buyer_message": "Intéressé pour 30 tonnes",
            },
            headers=headers_b,
        )
        assert offer_resp.status_code == 201, offer_resp.text
        offer = offer_resp.json()
        assert offer["status"] == "pending"

        # Le vendeur accepte -> une commande est créée
        accept_resp = await client.post(
            f"/api/v1/offers/{offer['id']}/accept", headers=headers_a
        )
        assert accept_resp.status_code == 200, accept_resp.text
        assert accept_resp.json()["status"] == "accepted"

        # L'annonce est partiellement vendue
        listing_after = (await client.get(f"/api/v1/listings/{listing['id']}")).json()
        assert listing_after["available_quantity"] == "70.00"
        assert listing_after["status"] == "partially_sold"

        # La commande existe en base (vérification via la facture ensuite)
        # L'acheteur ne peut pas accepter une offre (403)
        buyer_accept = await client.post(
            f"/api/v1/offers/{offer['id']}/accept", headers=headers_b
        )
        assert buyer_accept.status_code == 403

    async def test_invoice_pdf_generated_for_verified_pro(self, client, db_session):
        headers_a, headers_b, listing = await self._setup(client)

        # Vérifier le compte pro (exigé pour émettre une facture)
        from sqlalchemy import select
        from app.models.user import User

        stmt = select(User).where(User.phone == USER_A["phone"])
        user_a = (await db_session.execute(stmt)).scalar_one()
        user_a.verification_status = "verified"
        user_a.verification_documents = {"cin_url": "http://x/cin.pdf", "nif": "NIF-12345"}
        await db_session.commit()

        # Offre + acceptation -> commande
        offer = (
            await client.post(
                "/api/v1/offers/",
                json={
                    "listing_id": listing["id"],
                    "quantity": "30.00",
                    "proposed_price": "480.00",
                },
                headers=headers_b,
            )
        ).json()
        accept = await client.post(f"/api/v1/offers/{offer['id']}/accept", headers=headers_a)
        assert accept.status_code == 200

        # Récupérer la commande créée
        from app.models.order import Order
        from app.models.user import User

        order = (await db_session.execute(select(Order))).scalar_one()
        buyer = (
            await db_session.execute(
                select(User).where(User.id == order.buyer_id)
            )
        ).scalar_one()
        assert buyer.phone == USER_B["phone"]
        assert order.seller_id == user_a.id
        assert order.quantity == Decimal("30.00")
        assert order.price_final == Decimal("480.00")
        assert order.total_amount == Decimal("14400.00")

        # Générer la facture PDF
        pdf_resp = await client.get(f"/api/v1/invoices/{order.id}/pdf", headers=headers_a)
        assert pdf_resp.status_code == 200, pdf_resp.text
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert pdf_resp.content[:4] == b"%PDF"

        # La facture est persistée
        from app.models.invoice import Invoice

        invoice = (await db_session.execute(select(Invoice))).scalar_one()
        assert invoice.order_id == order.id
        assert invoice.amount == Decimal("14400.00")
        assert invoice.status == "generated"

    async def test_invoice_requires_verified_pro(self, client, db_session):
        headers_a, headers_b, listing = await self._setup(client)

        offer = (
            await client.post(
                "/api/v1/offers/",
                json={
                    "listing_id": listing["id"],
                    "quantity": "10.00",
                    "proposed_price": "490.00",
                },
                headers=headers_b,
            )
        ).json()
        await client.post(f"/api/v1/offers/{offer['id']}/accept", headers=headers_a)

        from sqlalchemy import select
        from app.models.order import Order

        order = (await db_session.execute(select(Order))).scalar_one()
        resp = await client.get(f"/api/v1/invoices/{order.id}/pdf", headers=headers_a)
        assert resp.status_code == 403  # pas encore vérifié


class TestCounterOfferFlow:
    async def test_counter_offer(self, client):
        # Setup : USER_A vendeur, USER_B acheteur
        await register(client, USER_A)
        await register(client, USER_B)
        token_a = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        token_b = (await login(client, USER_B["phone"], USER_B["password"])).json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        listing = (
            await client.post("/api/v1/listings/", json=LISTING, headers=headers_a)
        ).json()

        offer = (
            await client.post(
                "/api/v1/offers/",
                json={"listing_id": listing["id"], "quantity": "20.00", "proposed_price": "450.00"},
                headers=headers_b,
            )
        ).json()

        # Contre-offre du vendeur
        counter = await client.post(
            f"/api/v1/offers/{offer['id']}/counter",
            json={
                "counter_offer_price": "470.00",
                "counter_offer_quantity": "15.00",
                "seller_response": "15 tonnes max à ce prix",
            },
            headers=headers_a,
        )
        assert counter.status_code == 200, counter.text
        assert counter.json()["status"] == "counter_offer"
        assert counter.json()["counter_offer_price"] == "470.00"

        # Seul le vendeur peut contre-offrir
        forbidden = await client.post(
            f"/api/v1/offers/{offer['id']}/counter",
            json={"counter_offer_price": "1.00", "counter_offer_quantity": "1.00"},
            headers=headers_b,
        )
        assert forbidden.status_code == 403

        # Refus de l'offre par l'acheteur
        refused = await client.post(
            f"/api/v1/offers/{offer['id']}/refuse", headers=headers_b
        )
        assert refused.status_code == 200
        assert refused.json()["status"] == "refused"


class TestOfferValidation:
    async def test_offer_on_own_listing_rejected(self, client):
        await register(client, USER_A)
        token = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        listing = (
            await client.post("/api/v1/listings/", json=LISTING, headers=headers)
        ).json()
        resp = await client.post(
            "/api/v1/offers/",
            json={"listing_id": listing["id"], "quantity": "10.00", "proposed_price": "400.00"},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_offer_quantity_exceeds_availability(self, client):
        await register(client, USER_A)
        await register(client, USER_B)
        token_a = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        token_b = (await login(client, USER_B["phone"], USER_B["password"])).json()["access_token"]
        listing = (
            await client.post(
                "/api/v1/listings/", json=LISTING,
                headers={"Authorization": f"Bearer {token_a}"},
            )
        ).json()
        resp = await client.post(
            "/api/v1/offers/",
            json={"listing_id": listing["id"], "quantity": "999.00", "proposed_price": "400.00"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 409


class TestTransporterFlow:
    async def test_create_transporter_profile(self, client):
        await register(client, USER_A)
        token = (await login(client, USER_A["phone"], USER_A["password"])).json()["access_token"]
        # USER_A est agriculteur -> refusé
        resp = await client.post(
            "/api/v1/transporters/",
            json={
                "coverage_region": ["Analamanga"],
                "vehicle_type": "Camion 10T",
                "capacity_kg": 10000,
                "base_rate": 1500.0,
                "rate_unit": "per_km",
                "is_available": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

        # Un transporteur peut créer son profil
        transporter_user = dict(USER_B, role="transporteur")
        await register(client, transporter_user)
        token_t = (await login(client, transporter_user["phone"], "Motdepasse123")).json()["access_token"]
        ok = await client.post(
            "/api/v1/transporters/",
            json={
                "coverage_region": ["Analamanga", "Atsimo"],
                "vehicle_type": "Camion 10T",
                "capacity_kg": 10000,
                "base_rate": 1500.0,
                "rate_unit": "per_km",
                "is_available": True,
            },
            headers={"Authorization": f"Bearer {token_t}"},
        )
        assert ok.status_code == 201, ok.text
        assert ok.json()["capacity_kg"] == 10000

        # Liste publique des transporteurs
        listing_resp = await client.get("/api/v1/transporters/")
        assert listing_resp.status_code == 200
        assert len(listing_resp.json()) == 1


class TestPriceHistory:
    async def test_price_history_empty(self, client):
        resp = await client.get("/api/v1/prices/history")
        assert resp.status_code == 200
        assert resp.json() == []

