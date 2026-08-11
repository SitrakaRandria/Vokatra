# Vokatra API

**Plateforme agricole Madagascar** — API FastAPI pour la mise en relation des
agriculteurs, collecteurs, grossistes et transporteurs.

## Fonctionnalités

- **Authentification JWT** — inscription/connexion par téléphone malgache
  (`+261XXXXXXXXX`), hachage bcrypt, validation stricte des mots de passe
- **Annonces (listings)** — CRUD complet, filtres avancés (produit, région,
  prix, quantité, saison), pagination, badge de saisonnalité automatique
- **Négociation (offers)** — offres, contre-offres, acceptation/refus,
  expiration automatique à 7 jours
- **Commandes (orders)** — création automatique à l'acceptation d'une offre,
  cycle de vie `pending → confirmed → delivered/cancelled`
- **Factures (invoices)** — génération PDF pour les comptes professionnels
  vérifiés (reportlab)
- **Transporteurs** — profils avec zones couvertes, capacité, tarifs
- **Historique des prix** — consultation par produit/région sur 12–24 mois
- **Chat temps réel** — WebSocket authentifié par JWT, conversations
  acheteur/vendeur, accusés de lecture

## Architecture

```
backend/
├── app/
│   ├── api/            # Routers FastAPI (v1 + WebSocket)
│   │   ├── v1/         # auth, listings, offers, transporters, invoices, prices
│   │   └── websocket/  # chat temps réel
│   ├── core/           # Configuration, base de données, auth, saisonnalité
│   ├── models/         # Modèles SQLAlchemy 2.0 (Mapped/mapped_column)
│   ├── schemas/        # Schémas Pydantic v2 avec validation métier
│   ├── utils/          # Validateurs, PDF, Cloudinary, helpers temporels
│   └── websocket/      # Gestionnaire de connexions
├── tests/              # Tests pytest (unitaires + intégration API)
└── pyproject.toml
```

## Prérequis

- Python 3.10+
- PostgreSQL 14+ (ou SQLite via `aiosqlite` pour les tests)
- Compte [Cloudinary](https://cloudinary.com) pour l'upload d'images

## Installation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configuration
cp .env.example .env
# Éditez .env avec vos identifiants (DATABASE_URL, JWT_SECRET_KEY, Cloudinary)
```

## Lancement

```bash
uvicorn app.main:app --reload
```

L'API est disponible sur `http://localhost:8000`. La documentation interactive
est activée en mode debug : `http://localhost:8000/api/docs`.

Point de contrôle de santé : `GET /health`.

## Tests

```bash
pytest
```

Les tests utilisent SQLite en mémoire — aucune base PostgreSQL requise.
Ils couvrent les validateurs, la configuration, l'authentification JWT, les
modèles métier (cycles de vie des annonces, offres, commandes, factures) et
les parcours API complets (inscription → annonce → offre → commande → facture).

## Variables d'environnement

| Variable | Requis | Défaut | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | URL PostgreSQL (`postgresql://…` → asyncpg auto) |
| `JWT_SECRET_KEY` | ✅ | — | Clé secrète JWT (min 32 caractères) |
| `CLOUDINARY_CLOUD_NAME` | ✅ | — | Cloud Cloudinary |
| `CLOUDINARY_API_KEY` | ✅ | — | Clé API Cloudinary |
| `CLOUDINARY_API_SECRET` | ✅ | — | Secret API Cloudinary |
| `DEBUG` | — | `false` | Active le mode debug + docs interactives |
| `ENVIRONMENT` | — | `development` | `development` / `production` / `test` |
| `CORS_ORIGINS` | — | localhost:3000, vokatra.mg | Origines CORS autorisées |

## Licence

MIT — voir [LICENSE](../LICENSE).
