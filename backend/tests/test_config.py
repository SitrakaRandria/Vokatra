"""
Tests de la configuration applicative.
"""
import pytest

from app.config import Settings


class TestDatabaseUrlValidation:
    """Validation et normalisation de DATABASE_URL."""

    def test_postgresql_auto_converted_to_asyncpg(self):
        """Une URL postgresql:// synchrone doit être convertie en asyncpg."""
        s = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/vokatra",
            JWT_SECRET_KEY="x" * 40,
            CLOUDINARY_CLOUD_NAME="c",
            CLOUDINARY_API_KEY="k",
            CLOUDINARY_API_SECRET="s",
        )
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/vokatra"

    def test_asyncpg_url_left_unchanged(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/vokatra",
            JWT_SECRET_KEY="x" * 40,
            CLOUDINARY_CLOUD_NAME="c",
            CLOUDINARY_API_KEY="k",
            CLOUDINARY_API_SECRET="s",
        )
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/vokatra"

    def test_sqlite_url_allowed(self):
        s = Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            JWT_SECRET_KEY="x" * 40,
            CLOUDINARY_CLOUD_NAME="c",
            CLOUDINARY_API_KEY="k",
            CLOUDINARY_API_SECRET="s",
        )
        assert s.DATABASE_URL == "sqlite+aiosqlite:///:memory:"

    @pytest.mark.parametrize("bad_url", [
        "mysql://user:pass@localhost/db",
        "mongodb://localhost/db",
        "sqlite:///plain.db",  # aiosqlite requis
        "http://localhost/db",
    ])
    def test_invalid_urls_rejected(self, bad_url):
        with pytest.raises(ValueError):
            Settings(
                DATABASE_URL=bad_url,
                JWT_SECRET_KEY="x" * 40,
                CLOUDINARY_CLOUD_NAME="c",
                CLOUDINARY_API_KEY="k",
                CLOUDINARY_API_SECRET="s",
            )


class TestJwtSecretValidation:
    """Validation de la clé secrète JWT."""

    def test_short_secret_rejected(self):
        with pytest.raises(ValueError):
            Settings(
                DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                JWT_SECRET_KEY="short",
                CLOUDINARY_CLOUD_NAME="c",
                CLOUDINARY_API_KEY="k",
                CLOUDINARY_API_SECRET="s",
            )

    def test_long_enough_secret_accepted(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
            JWT_SECRET_KEY="a" * 32,
            CLOUDINARY_CLOUD_NAME="c",
            CLOUDINARY_API_KEY="k",
            CLOUDINARY_API_SECRET="s",
        )
        assert s.JWT_SECRET_KEY == "a" * 32
