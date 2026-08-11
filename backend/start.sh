#!/bin/bash
# start.sh

set -e

echo "🚀 Démarrage de Vokatra Backend"
echo "📦 Installation des dépendances..."
pip install -r requirements.txt

echo "🔄 Exécution des migrations..."
alembic upgrade head

echo "✅ Démarrage du serveur..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
