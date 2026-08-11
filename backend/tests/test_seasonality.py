"""
Tests du calcul de saisonnalité (avec base SQLite).
"""
import pytest

from app.core.seasonality import compute_seasonality_badge
from app.models.seasonality import Seasonality


class TestComputeSeasonalityBadge:
    """Badge de saisonnalité selon la période du produit."""

    async def test_no_seasonality_data(self, db_session):
        result = await compute_seasonality_badge(
            product="Riz", region="Analamanga", current_month=6, session=db_session
        )
        assert result is False

    async def test_in_season_same_year(self, db_session):
        db_session.add(Seasonality(product="Mangue", region="Analamanga", month_start=10, month_end=12))
        await db_session.commit()
        assert await compute_seasonality_badge(
            product="Mangue", region="Analamanga", current_month=11, session=db_session
        ) is True
        assert await compute_seasonality_badge(
            product="Mangue", region="Analamanga", current_month=3, session=db_session
        ) is False

    async def test_out_of_season(self, db_session):
        db_session.add(Seasonality(product="Litchi", region="Atsinanana", month_start=1, month_end=3))
        await db_session.commit()
        assert await compute_seasonality_badge(
            product="Litchi", region="Atsinanana", current_month=7, session=db_session
        ) is False

    async def test_cross_year_season(self, db_session):
        """Saison novembre -> février : chevauchement d'année."""
        db_session.add(Seasonality(product="Vanille", region="Sava", month_start=11, month_end=2))
        await db_session.commit()
        assert await compute_seasonality_badge(
            product="Vanille", region="Sava", current_month=12, session=db_session
        ) is True
        assert await compute_seasonality_badge(
            product="Vanille", region="Sava", current_month=1, session=db_session
        ) is True
        assert await compute_seasonality_badge(
            product="Vanille", region="Sava", current_month=6, session=db_session
        ) is False

    async def test_boundary_months(self, db_session):
        """Les mois de début et fin sont inclus."""
        db_session.add(Seasonality(product="Raisin", region="Amoron'i Mania", month_start=4, month_end=6))
        await db_session.commit()
        assert await compute_seasonality_badge(
            product="Raisin", region="Amoron'i Mania", current_month=4, session=db_session
        ) is True
        assert await compute_seasonality_badge(
            product="Raisin", region="Amoron'i Mania", current_month=6, session=db_session
        ) is True
        assert await compute_seasonality_badge(
            product="Raisin", region="Amoron'i Mania", current_month=7, session=db_session
        ) is False
