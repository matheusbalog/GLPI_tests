import pytest
import httpx
import respx
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
BASE_URL = "http://glpi/apirest.php"

@respx.mock
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@respx.mock
def test_test_connection_success(monkeypatch):
    monkeypatch.setenv("GLPI_BASE_URL", BASE_URL)
    monkeypatch.setenv("GLPI_APP_TOKEN", "mock_app")
    monkeypatch.setenv("GLPI_USER_TOKEN", "mock_user")

    respx.get(f"{BASE_URL}/initSession").mock(
        return_value=httpx.Response(200, json={"session_token": "token_valida"})
    )
    respx.get(f"{BASE_URL}/killSession").mock(
        return_value=httpx.Response(200, json=["OK"])
    )

    response = client.post("/glpi/test-connection")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Conexao com GLPI 10.0.5 validada com sucesso."

@respx.mock
def test_get_ticket_endpoint(monkeypatch):
    monkeypatch.setenv("GLPI_BASE_URL", BASE_URL)
    monkeypatch.setenv("GLPI_APP_TOKEN", "mock_app")
    monkeypatch.setenv("GLPI_USER_TOKEN", "mock_user")

    respx.get(f"{BASE_URL}/initSession").mock(
        return_value=httpx.Response(200, json={"session_token": "token_valida"})
    )
    respx.get(f"{BASE_URL}/Ticket/15").mock(
        return_value=httpx.Response(200, json={"id": 15, "name": "Falha no faturamento", "content": "Nao gera nota", "status": 1})
    )
    respx.get(f"{BASE_URL}/killSession").mock(
        return_value=httpx.Response(200, json=["OK"])
    )

    response = client.get("/glpi/ticket/15")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 15
    assert data["name"] == "Falha no faturamento"
