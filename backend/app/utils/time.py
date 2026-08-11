"""
Helpers temporels communs à toute l'application.

Centralise la génération d'horodatages UTC conscient du fuseau horaire.
``datetime.utcnow()`` est déprécié depuis Python 3.12 et produit des
objets *naive* incompatibles avec les colonnes ``timestamptz`` de
PostgreSQL via asyncpg. Utiliser ``utcnow()`` partout à la place.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Retourne l'horodatage UTC courant, conscient du fuseau horaire.

    Returns:
        datetime: ``datetime.now(timezone.utc)``
    """
    return datetime.now(timezone.utc)
