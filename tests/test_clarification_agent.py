import pytest
import httpx
import respx
from agents.clarification_agent import ClarificationAgent, ClarificationResult
from tools.glpi_tools import GLPIClient

BASE_URL = "https://glpi.example.com"

@pytest.fixture
def glpi_client():
    client = GLPIClient(base_url=BASE_URL, app_token="mock_app", user_token="mock_user")
    client.session_token = "mock_session"
    return client

@pytest.fixture
def clarification_agent(glpi_client):
    return ClarificationAgent(glpi_client=glpi_client)

@respx.mock
def test_clarification_round_under_limit(clarification_agent):
    respx.post(f"{BASE_URL}/apirest.php/ITILFollowup").mock(
        return_value=httpx.Response(201, json={"id": 101, "message": "Followup criado"})
    )
    respx.put(f"{BASE_URL}/apirest.php/Ticket/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "message": "Status atualizado"})
    )

    result = clarification_agent.request_clarification(
        ticket_id=10,
        current_rounds=1,
        missing_fields=["passo_a_passo", "logs"]
    )

    assert isinstance(result, ClarificationResult)
    assert result.ticket_id == 10
    assert result.current_rounds == 2
    assert result.next_state == "WAITING_CUSTOMER"
    assert "passo_a_passo" in result.question_text

@respx.mock
def test_clarification_escalation_on_limit_exceeded(clarification_agent):
    respx.post(f"{BASE_URL}/apirest.php/ITILFollowup").mock(
        return_value=httpx.Response(201, json={"id": 102, "message": "Followup de escalonamento"})
    )

    result = clarification_agent.request_clarification(
        ticket_id=10,
        current_rounds=3,
        missing_fields=["evidencias"]
    )

    assert isinstance(result, ClarificationResult)
    assert result.ticket_id == 10
    assert result.next_state == "ESCALATED"
    assert result.escalated is True
    assert "limite de tentativas" in result.question_text.lower()
