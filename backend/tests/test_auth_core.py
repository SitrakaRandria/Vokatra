"""
Tests des fonctions d'authentification JWT et de hachage.
"""
from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

from app.config import settings
from app.core.auth import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
)


class TestJwtTokens:
    """Création et vérification des tokens JWT."""

    def test_create_and_verify_token(self):
        token = create_access_token(data={"sub": "42", "phone": "+261341234567"})
        payload = verify_token(token)
        assert payload["sub"] == "42"
        assert payload["phone"] == "+261341234567"
        assert "exp" in payload

    def test_token_requires_sub(self):
        with pytest.raises(ValueError):
            create_access_token(data={"phone": "+261341234567"})

    def test_token_custom_expiry(self):
        token = create_access_token(
            data={"sub": "1"}, expires_delta=timedelta(minutes=5)
        )
        payload = verify_token(token)
        # exp doit être proche de maintenant + 5 minutes
        from app.utils.time import utcnow

        expected = utcnow() + timedelta(minutes=5)
        assert abs(payload["exp"] - expected.timestamp()) < 60

    def test_token_signing_and_verification_roundtrip(self):
        """Le token est signé avec la clé configurée."""
        token = create_access_token(data={"sub": "7"})
        decoded = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert decoded["sub"] == "7"

    def test_tampered_token_rejected(self):
        token = create_access_token(data={"sub": "1"})
        # Altération du payload (dernier segment)
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1][:-1] + "x" + "." + parts[2]
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered)
        assert exc_info.value.status_code == 401

    def test_garbage_token_rejected(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-jwt")
        assert exc_info.value.status_code == 401


class TestPasswordHashing:
    """Hachage et vérification des mots de passe."""

    def test_hash_and_verify(self):
        hashed = get_password_hash("Motdepasse123")
        assert hashed != "Motdepasse123"
        assert verify_password("Motdepasse123", hashed) is True

    def test_wrong_password_rejected(self):
        hashed = get_password_hash("Motdepasse123")
        assert verify_password("Wrongpass123", hashed) is False

    def test_hashes_are_unique(self):
        h1 = get_password_hash("Motdepasse123")
        h2 = get_password_hash("Motdepasse123")
        assert h1 != h2  # sel bcrypt différent
