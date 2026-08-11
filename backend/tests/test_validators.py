"""
Tests des validateurs métier.
"""
from decimal import Decimal

import pytest

from app.utils.validators import (
    validate_phone_madagascar,
    validate_positive_decimal,
    validate_non_negative_decimal,
    normalize_phone,
    validate_region,
)


class TestValidatePhoneMadagascar:
    """Validation des numéros de téléphone malgaches."""

    @pytest.mark.parametrize("phone", [
        "+261341234567",
        "+261 34 123 4567",
        "+261-34-123-4567",
        "261341234567",
        "0341234567",
        "+261201234567",
        "+261331234567",
    ])
    def test_valid_phones(self, phone):
        assert validate_phone_madagascar(phone) is True

    @pytest.mark.parametrize("phone", [
        "",
        None,
        "+2611234567",          # trop court
        "+2613412345678",       # trop long
        "+26134123456",         # préfixe inconnu
        "034123456",            # préfixe 34 absent
        "+261781234567",        # indicatif inconnu
        "+33612345678",         # numéro français
        "abc",
        "1234567890",
    ])
    def test_invalid_phones(self, phone):
        assert validate_phone_madagascar(phone) is False


class TestNormalizePhone:
    """Normalisation des numéros au format international."""

    @pytest.mark.parametrize("raw,expected", [
        ("0341234567", "+261341234567"),
        ("261341234567", "+261341234567"),
        ("+261341234567", "+261341234567"),
        ("+261 34 123 4567", "+261341234567"),
        ("034 12 345 67", "+261341234567"),
    ])
    def test_normalization(self, raw, expected):
        assert normalize_phone(raw) == expected

    @pytest.mark.parametrize("raw", ["", None, "12345", "abcd"])
    def test_invalid_returns_none(self, raw):
        assert normalize_phone(raw) is None


class TestDecimalValidators:
    """Validateurs de nombres décimaux."""

    def test_positive_decimal(self):
        assert validate_positive_decimal(Decimal('1.5')) is True
        assert validate_positive_decimal(Decimal('0.01')) is True
        assert validate_positive_decimal(Decimal('0')) is False
        assert validate_positive_decimal(Decimal('-1')) is False
        assert validate_positive_decimal(None) is False
        assert validate_positive_decimal("abc") is False

    def test_non_negative_decimal(self):
        assert validate_non_negative_decimal(Decimal('0')) is True
        assert validate_non_negative_decimal(Decimal('2')) is True
        assert validate_non_negative_decimal(Decimal('-1')) is False
        assert validate_non_negative_decimal(None) is False


class TestValidateRegion:
    """Validation des régions."""

    def test_valid_region(self):
        assert validate_region("Analamanga", ["Analamanga", "Atsimo"]) is True

    def test_invalid_region(self):
        assert validate_region("Paris", ["Analamanga"]) is False
        assert validate_region("", ["Analamanga"]) is False
        assert validate_region("Analamanga", []) is False
