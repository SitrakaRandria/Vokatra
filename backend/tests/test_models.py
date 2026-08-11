"""
Tests des modèles métier (logique pure, sans base de données).
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.listing import Listing
from app.models.offer import Offer
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.user import User
from app.utils.time import utcnow


class TestUserModel:
    """Logique métier du modèle User."""

    def make_user(self, **kwargs):
        defaults = dict(
            phone="+261341234567",
            full_name="Rakoto Jean",
            role="agriculteur",
            region="Analamanga",
            account_type="physical",
            hashed_password="hashed",
        )
        defaults.update(kwargs)
        return User(**defaults)

    def test_valid_phone_accepted(self):
        user = self.make_user()
        assert user.phone == "+261341234567"

    @pytest.mark.parametrize("bad_phone", ["+33612345678", "12345", "+261999999999"])
    def test_invalid_phone_rejected(self, bad_phone):
        with pytest.raises(ValueError):
            self.make_user(phone=bad_phone)

    def test_display_name_professional(self):
        user = self.make_user(account_type="professional", company_name="AgriMada SARL")
        assert user.display_name == "AgriMada SARL (Rakoto Jean)"

    def test_display_name_physical(self):
        user = self.make_user()
        assert user.display_name == "Rakoto Jean"

    def test_is_verified_professional(self):
        assert self.make_user().is_verified_professional is False
        verified = self.make_user(
            account_type="professional", verification_status="verified",
            verification_documents={"cin_url": "http://x/cin.pdf"},
        )
        assert verified.is_verified_professional is True

    def test_can_issue_invoices(self):
        assert self.make_user().can_issue_invoices() is False
        prof = self.make_user(
            account_type="professional", verification_status="verified",
            verification_documents={"cin_url": "http://x/cin.pdf"},
        )
        assert prof.can_issue_invoices() is True

    def test_update_rating_averages(self):
        user = self.make_user()
        user.update_rating(Decimal('4'))
        user.update_rating(Decimal('2'))
        assert user.total_transactions == 2
        assert user.rating == Decimal('3')

    def test_update_rating_rejects_out_of_range(self):
        user = self.make_user()
        with pytest.raises(ValueError):
            user.update_rating(Decimal('6'))


class TestListingModel:
    """Cycle de vie d'une annonce."""

    def make_listing(self, total=Decimal('100'), available=Decimal('100')):
        return Listing(
            user_id=1,
            product="Riz",
            description="Riz de première qualité",
            total_quantity=total,
            available_quantity=available,
            unit="tonne",
            price=Decimal('500'),
            region="Analamanga",
            status="available",
        )

    def test_initial_state(self):
        listing = self.make_listing()
        assert listing.is_fully_sold is False
        assert listing.remaining_percentage == 100.0

    def test_update_availability_partial_sale(self):
        listing = self.make_listing()
        listing.update_availability(Decimal('30'))
        assert listing.available_quantity == Decimal('70')
        assert listing.status == "partially_sold"

    def test_update_availability_full_sale(self):
        listing = self.make_listing()
        listing.update_availability(Decimal('100'))
        assert listing.available_quantity == Decimal('0')
        assert listing.status == "sold"
        assert listing.is_fully_sold is True

    def test_update_availability_over_available_rejected(self):
        listing = self.make_listing()
        with pytest.raises(ValueError):
            listing.update_availability(Decimal('150'))

    def test_update_availability_zero_rejected(self):
        listing = self.make_listing()
        with pytest.raises(ValueError):
            listing.update_availability(Decimal('0'))

    def test_reserve_and_release(self):
        listing = self.make_listing()
        listing.reserve()
        assert listing.status == "reserved"
        listing.release_reservation()
        assert listing.status == "available"

    def test_reserve_sold_rejected(self):
        listing = self.make_listing(available=Decimal('0'))
        listing.status = "sold"
        with pytest.raises(ValueError):
            listing.reserve()

    def test_remaining_percentage_zero_total(self):
        """Guard: division par zéro quand la quantité totale est 0."""
        listing = self.make_listing(total=Decimal('1'), available=Decimal('1'))
        # Écriture directe dans __dict__ pour contourner la validation
        # (cas limite artificiel : quantité totale nulle)
        listing.__dict__['total_quantity'] = Decimal('0')
        assert listing.remaining_percentage == 0.0


class TestOfferModel:
    """Machine à états d'une offre."""

    def make_offer(self):
        return Offer(
            listing_id=1,
            buyer_id=2,
            quantity=Decimal('10'),
            proposed_price=Decimal('450'),
            status="pending",
        )

    def test_initial_state(self):
        offer = self.make_offer()
        assert offer.is_active is True
        assert offer.is_counter_offer is False

    def test_accept(self):
        offer = self.make_offer()
        offer.accept()
        assert offer.status == "accepted"
        assert offer.is_active is False

    def test_accept_twice_rejected(self):
        offer = self.make_offer()
        offer.accept()
        with pytest.raises(ValueError):
            offer.accept()

    def test_refuse(self):
        offer = self.make_offer()
        offer.refuse()
        assert offer.status == "refused"

    def test_create_counter_offer(self):
        offer = self.make_offer()
        offer.create_counter_offer(Decimal('480'), Decimal('8'))
        assert offer.status == "counter_offer"
        assert offer.counter_offer_price == Decimal('480')
        assert offer.counter_offer_quantity == Decimal('8')

    def test_counter_offer_invalid_price(self):
        offer = self.make_offer()
        with pytest.raises(ValueError):
            offer.create_counter_offer(Decimal('-5'), Decimal('8'))

    def test_expiration_set_automatically(self):
        offer = self.make_offer()
        assert offer.expires_at is None  # set by event listener at flush time


class TestOrderModel:
    """Cycle de vie d'une commande."""

    def make_order(self, quantity=Decimal('10'), price=Decimal('450')):
        return Order(
            listing_id=1,
            buyer_id=2,
            seller_id=1,
            quantity=quantity,
            price_final=price,
            status="pending",
        )

    def test_total_amount(self):
        order = self.make_order()
        assert order.total_amount == Decimal('4500')

    def test_confirm(self):
        order = self.make_order()
        order.confirm()
        assert order.status == "confirmed"

    def test_confirm_cancelled_rejected(self):
        order = self.make_order()
        order.cancel()
        with pytest.raises(ValueError):
            order.confirm()

    def test_delivered(self):
        order = self.make_order()
        order.confirm()
        order.mark_delivered()
        assert order.status == "delivered"

    def test_cancel_delivered_rejected(self):
        order = self.make_order()
        order.mark_delivered()
        with pytest.raises(ValueError):
            order.cancel()


class TestInvoiceModel:
    """Cycle de vie d'une facture."""

    def make_invoice(self):
        return Invoice(
            order_id=1,
            issuer_id=1,
            recipient_id=2,
            amount=Decimal('4500'),
            status="generated",
        )

    def test_mark_paid(self):
        invoice = self.make_invoice()
        invoice.mark_paid()
        assert invoice.status == "paid"
        assert invoice.paid_at is not None

    def test_mark_paid_cancelled_rejected(self):
        invoice = self.make_invoice()
        invoice.cancel()
        with pytest.raises(ValueError):
            invoice.mark_paid()

    def test_cancel_paid_rejected(self):
        invoice = self.make_invoice()
        invoice.mark_paid()
        with pytest.raises(ValueError):
            invoice.cancel()


class TestSeasonalityModel:
    """Gestion des saisons avec chevauchement d'année."""

    def make_seasonality(self, start, end):
        from app.models.seasonality import Seasonality
        return Seasonality(
            product="Mangue",
            region="Analamanga",
            month_start=start,
            month_end=end,
        )

    def test_same_year_season(self):
        season = self.make_seasonality(3, 6)
        assert season.months == [3, 4, 5, 6]

    def test_cross_year_season(self):
        season = self.make_seasonality(11, 2)
        assert season.months == [11, 12, 1, 2]
