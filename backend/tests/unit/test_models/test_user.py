"""
Tests unitaires pour le modèle User.
"""
import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.core.auth import get_password_hash

@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test de création d'un utilisateur valide."""
    user = User(
        phone="+261321234567",
        full_name="Jean Dupont",
        role="agriculteur",
        region="Analamanga",
        account_type="physical",
        hashed_password=get_password_hash("Test123!")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id is not None
    assert user.phone == "+261321234567"
    assert user.full_name == "Jean Dupont"
    assert user.role == "agriculteur"
    assert user.verification_status == "base"
    assert user.rating == Decimal('0.00')

@pytest.mark.asyncio
async def test_validate_phone_format(db_session):
    """Test de validation du format de téléphone."""
    # Téléphone invalide
    with pytest.raises(ValueError, match="Format de téléphone invalide"):
        user = User(
            phone="123456789",
            full_name="Test User",
            role="agriculteur",
            region="Analamanga",
            hashed_password=get_password_hash("Test123!")
        )
        db_session.add(user)
        await db_session.commit()

@pytest.mark.asyncio
async def test_duplicate_phone(db_session):
    """Test de l'unicité du téléphone."""
    user1 = User(
        phone="+261321234567",
        full_name="User 1",
        role="agriculteur",
        region="Analamanga",
        hashed_password=get_password_hash("Test123!")
    )
    db_session.add(user1)
    await db_session.commit()
    
    user2 = User(
        phone="+261321234567",  # Même téléphone
        full_name="User 2",
        role="agriculteur",
        region="Analamanga",
        hashed_password=get_password_hash("Test123!")
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
        await db_session.rollback()

@pytest.mark.asyncio
async def test_update_rating(db_session, test_user):
    """Test de mise à jour de la note."""
    assert test_user.rating == Decimal('0.00')
    assert test_user.total_transactions == 0
    
    test_user.update_rating(4.5)
    assert test_user.rating == Decimal('4.50')
    assert test_user.total_transactions == 1
    
    test_user.update_rating(5.0)
    assert test_user.rating == Decimal('4.75')
    assert test_user.total_transactions == 2

@pytest.mark.asyncio
async def test_invalid_rating(db_session, test_user):
    """Test de validation des notes invalides."""
    with pytest.raises(ValueError, match="Note invalide"):
        test_user.update_rating(6.0)
    
    with pytest.raises(ValueError, match="Note invalide"):
        test_user.update_rating(-1.0)

@pytest.mark.asyncio
async def test_can_issue_invoices(db_session):
    """Test de la vérification des factures."""
    # Compte physique non vérifié
    user = User(
        phone="+261321234567",
        full_name="Test User",
        role="agriculteur",
        region="Analamanga",
        account_type="physical",
        verification_status="base",
        hashed_password=get_password_hash("Test123!")
    )
    assert user.can_issue_invoices() is False
    
    # Compte professionnel non vérifié
    user.account_type = "professional"
    assert user.can_issue_invoices() is False
    
    # Compte professionnel vérifié
    user.verification_status = "verified"
    user.verification_documents = {"cin_url": "http://test.com/cin.jpg"}
    assert user.can_issue_invoices() is True
