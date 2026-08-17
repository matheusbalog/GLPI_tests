# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
import respx
from tools.glpi_tools import (
    GLPIClient, 
    GLPIAuthError, 
    GLPINotFoundError, 
    GLPIBadRequestError,
    TicketResponse
)

@pytest.fixture
def glpi_client():
    """Fixture to provide a clean GLPIClient instance for tests."""
    return GLPIClient(
        base_url="https://glpi.example.com",
        app_token="mock_app_token",
        user_token="mock_user_token"
    )

@respx.mock
def test_init_session_success(glpi_client):
    """Test successful session initialization."""
    respx.get("https://glpi.example.com/apirest.php/initSession").mock(
        return_value=httpx.Response(200, json={"session_token": "mock_session_token"})
    )
    
    token = glpi_client.init_session()
    
    assert token == "mock_session_token"
    assert glpi_client.session_token == "mock_session_token"

@respx.mock
def test_init_session_unauthorized(glpi_client):
    """Test session initialization with invalid credentials (401)."""
    respx.get("https://glpi.example.com/apirest.php/initSession").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    
    with pytest.raises(GLPIAuthError, match="Unauthorized"):
        glpi_client.init_session()

@respx.mock
def test_get_ticket_success(glpi_client):
    """Test successful ticket retrieval."""
    glpi_client.session_token = "mock_session_token"
    
    ticket_data = {
        "id": 123,
        "name": "Test Ticket",
        "content": "This is a test ticket regarding an issue.",
        "status": 1
    }
    
    # Mocking the GET request for the ticket
    request = respx.get("https://glpi.example.com/apirest.php/Ticket/123").mock(
        return_value=httpx.Response(200, json=ticket_data)
    )
    
    ticket = glpi_client.get_ticket(123)
    
    assert isinstance(ticket, TicketResponse)
    assert ticket.id == 123
    assert ticket.name == "Test Ticket"
    assert ticket.content == "This is a test ticket regarding an issue."
    
    # Ensure guardrail header was sent
    assert request.calls[0].request.headers["X-GLPI-Sanitized-Content"] == "false"

@respx.mock
def test_get_ticket_not_found(glpi_client):
    """Test ticket retrieval when ticket does not exist (404)."""
    glpi_client.session_token = "mock_session_token"
    
    respx.get("https://glpi.example.com/apirest.php/Ticket/999").mock(
        return_value=httpx.Response(404, json={"error": "Not Found"})
    )
    
    with pytest.raises(GLPINotFoundError, match="Not Found"):
        glpi_client.get_ticket(999)

@respx.mock
def test_add_followup_success(glpi_client):
    """Test successful followup creation."""
    glpi_client.session_token = "mock_session_token"
    
    request = respx.post("https://glpi.example.com/apirest.php/ITILFollowup").mock(
        return_value=httpx.Response(201, json={"id": 456, "message": "Followup added successfully"})
    )
    
    response = glpi_client.add_followup(123, "Please provide more details.")
    
    assert response["id"] == 456
    # Ensure guardrail header was sent
    assert request.calls[0].request.headers["X-GLPI-Sanitized-Content"] == "false"

@respx.mock
def test_add_followup_bad_request(glpi_client):
    """Test followup creation with bad data (400)."""
    glpi_client.session_token = "mock_session_token"
    
    respx.post("https://glpi.example.com/apirest.php/ITILFollowup").mock(
        return_value=httpx.Response(400, json={"error": "Bad Request"})
    )
    
    with pytest.raises(GLPIBadRequestError, match="Bad Request"):
        glpi_client.add_followup(123, "Invalid followup data")

@respx.mock
def test_kill_session_success(glpi_client):
    """Test successful session termination."""
    glpi_client.session_token = "mock_session_token"
    
    respx.get("https://glpi.example.com/apirest.php/killSession").mock(
        return_value=httpx.Response(200, json={"message": "Session killed"})
    )
    
    glpi_client.kill_session()
    
    assert glpi_client.session_token is None

def test_uninitialized_session(glpi_client):
    """Test calling authenticated endpoints without a session token."""
    with pytest.raises(GLPIAuthError, match="Session not initialized"):
        glpi_client.get_ticket(123)
        
    with pytest.raises(GLPIAuthError, match="Session not initialized"):
        glpi_client.add_followup(123, "Test")
