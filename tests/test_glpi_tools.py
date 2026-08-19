import pytest
import httpx
import respx
from tools.glpi_tools import (
    GLPIClient,
    GLPIAuthError,
    GLPINotFoundError,
    GLPIBadRequestError,
    TicketResponse,
    FollowupResponse,
    SolutionResponse,
)

BASE_URL = "https://glpi.example.com"

@pytest.fixture
def glpi_client():
    return GLPIClient(
        base_url=BASE_URL,
        app_token="test_app_token",
        user_token="test_user_token"
    )

@respx.mock
def test_init_session(glpi_client):
    respx.get(f"{BASE_URL}/apirest.php/initSession").mock(
        return_value=httpx.Response(200, json={"session_token": "token_123"})
    )
    token = glpi_client.init_session()
    assert token == "token_123"
    assert glpi_client.session_token == "token_123"

@respx.mock
def test_init_session_auth_error(glpi_client):
    respx.get(f"{BASE_URL}/apirest.php/initSession").mock(
        return_value=httpx.Response(401, json=["ERROR_LOGIN_PARAMETERS_MISSING"])
    )
    with pytest.raises(GLPIAuthError):
        glpi_client.init_session()

@respx.mock
def test_get_ticket(glpi_client):
    glpi_client.session_token = "token_123"
    respx.get(f"{BASE_URL}/apirest.php/Ticket/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "name": "Erro no login", "content": "Descricao", "status": 1})
    )
    ticket = glpi_client.get_ticket(10)
    assert isinstance(ticket, TicketResponse)
    assert ticket.id == 10
    assert ticket.name == "Erro no login"

@respx.mock
def test_get_ticket_not_found(glpi_client):
    glpi_client.session_token = "token_123"
    respx.get(f"{BASE_URL}/apirest.php/Ticket/999").mock(
        return_value=httpx.Response(404, json=["ERROR_RESOURCE_NOT_FOUND"])
    )
    with pytest.raises(GLPINotFoundError):
        glpi_client.get_ticket(999)

@respx.mock
def test_get_followups(glpi_client):
    glpi_client.session_token = "token_123"
    respx.get(f"{BASE_URL}/apirest.php/Ticket/10/ITILFollowup").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "items_id": 10, "content": "Primeira resposta"}])
    )
    followups = glpi_client.get_followups(10)
    assert len(followups) == 1
    assert isinstance(followups[0], FollowupResponse)
    assert followups[0].id == 1
    assert followups[0].content == "Primeira resposta"

@respx.mock
def test_add_followup(glpi_client):
    glpi_client.session_token = "token_123"
    route = respx.post(f"{BASE_URL}/apirest.php/ITILFollowup").mock(
        return_value=httpx.Response(201, json={"id": 50, "message": "Item adicionado"})
    )
    res = glpi_client.add_followup(10, "Solicito mais detalhes sobre o erro.")
    assert res["id"] == 50
    assert route.calls[0].request.headers["X-GLPI-Sanitized-Content"] == "false"

@respx.mock
def test_update_ticket_status(glpi_client):
    glpi_client.session_token = "token_123"
    respx.put(f"{BASE_URL}/apirest.php/Ticket/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "message": "Item atualizado"})
    )
    res = glpi_client.update_ticket_status(10, status=4)
    assert res["id"] == 10

@respx.mock
def test_add_solution(glpi_client):
    glpi_client.session_token = "token_123"
    respx.post(f"{BASE_URL}/apirest.php/ITILSolution").mock(
        return_value=httpx.Response(201, json={"id": 80, "message": "Solucao criada"})
    )
    sol = glpi_client.add_solution(10, "Problema corrigido no commit abc.")
    assert isinstance(sol, SolutionResponse)
    assert sol.id == 80

@respx.mock
def test_kill_session(glpi_client):
    glpi_client.session_token = "token_123"
    respx.get(f"{BASE_URL}/apirest.php/killSession").mock(
        return_value=httpx.Response(200, json=["OK"])
    )
    glpi_client.kill_session()
    assert glpi_client.session_token is None

@respx.mock
def test_context_manager():
    respx.get(f"{BASE_URL}/apirest.php/initSession").mock(
        return_value=httpx.Response(200, json={"session_token": "token_ctx"})
    )
    respx.get(f"{BASE_URL}/apirest.php/killSession").mock(
        return_value=httpx.Response(200, json=["OK"])
    )
    with GLPIClient(base_url=BASE_URL, app_token="a", user_token="u") as client:
        assert client.session_token == "token_ctx"
    assert client.session_token is None
