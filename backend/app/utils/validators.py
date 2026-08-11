"""
Fonctions de validation pour l'application Vokatra.
"""
import re
from typing import Optional
from decimal import Decimal

def validate_phone_madagascar(phone: str) -> bool:
    """
    Valide un numéro de téléphone malgache.
    
    Format: +261XXXXXXXXX (13 chiffres au total)
    
    Args:
        phone: Numéro à valider
        
    Returns:
        bool: True si le numéro est valide
    """
    if not phone:
        return False
    
    # Nettoie le numéro
    clean_phone = re.sub(r'[+\s-]', '', phone)
    if not clean_phone:
        return False
    
    # Accepte les formats +261XXXXXXXXX, 261XXXXXXXXX et 0XXXXXXXXX
    if clean_phone.startswith('0'):
        clean_phone = f"261{clean_phone[1:]}"
    elif clean_phone.startswith('261'):
        clean_phone = clean_phone
    else:
        return False
    
    # Vérifie le format
    pattern = r'^261(20|30|32|33|34|38|39)\d{7}$'
    return bool(re.match(pattern, clean_phone))

def validate_positive_decimal(value: Decimal) -> bool:
    """
    Valide qu'un Decimal est positif.
    
    Args:
        value: Valeur à valider
        
    Returns:
        bool: True si la valeur est > 0
    """
    try:
        return value is not None and value > Decimal('0')
    except (TypeError, ValueError):
        return False

def validate_non_negative_decimal(value: Decimal) -> bool:
    """
    Valide qu'un Decimal est non négatif.
    
    Args:
        value: Valeur à valider
        
    Returns:
        bool: True si la valeur est >= 0
    """
    try:
        return value is not None and value >= Decimal('0')
    except (TypeError, ValueError):
        return False

def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalise un numéro de téléphone au format standard.
    
    Args:
        phone: Numéro à normaliser
        
    Returns:
        Optional[str]: Numéro normalisé ou None si invalide
    """
    if not phone:
        return None
    
    # Enlève les espaces, tirets, etc.
    clean = re.sub(r'[+\s-]', '', phone)
    
    # Si le numéro commence par 0, ajoute +261
    if clean.startswith('0'):
        return f"+261{clean[1:]}"
    
    # Si le numéro commence par 261, ajoute +
    if clean.startswith('261'):
        return f"+{clean}"
    
    return None

def validate_region(region: str, allowed_regions: list) -> bool:
    """
    Valide qu'une région est dans la liste autorisée.
    
    Args:
        region: Région à valider
        allowed_regions: Liste des régions autorisées
        
    Returns:
        bool: True si la région est valide
    """
    if not region or not allowed_regions:
        return False
    return region in allowed_regions

def calculate_seasonality(product: str, region: str, current_month: int) -> bool:
    """
    Calcule la saisonnalité d'un produit dans une région.
    
    Args:
        product: Nom du produit
        region: Région
        current_month: Mois actuel (1-12)
        
    Returns:
        bool: True si le produit est en saison
    """
    # À implémenter avec la table Seasonality
    # Cette fonction sera appelée par les services
    return False
