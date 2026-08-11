"""
Tests pour le WebSocket de chat.
"""
import pytest
import json
from httpx import AsyncClient
from app.core.auth import create_access_token

@pytest.mark.asyncio
async def test_websocket_connection(client: AsyncClient, test_user):
    """Test de connexion WebSocket."""
    token = create_access_token(
        data={"sub": str(test_user.id), "phone": test_user.phone}
    )
    
    # Connexion WebSocket
    async with client.websocket_connect(f"/api/v1/chat/ws/{token}") as websocket:
        assert websocket is not None
        
        # Envoi d'un message ping
        await websocket.send_text(json.dumps({"action": "ping"}))
        
        # Réception de la réponse (ou erreur)
        response = await websocket.receive_text()
        # La réponse devrait contenir une erreur car "ping" n'est pas reconnu
        data = json.loads(response)
        assert "error" in data
