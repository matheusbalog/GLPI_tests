# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class GLPIException(Exception):
    """Base exception for GLPI errors."""
    pass

class GLPIAuthError(GLPIException):
    """Exception raised for authentication errors (401)."""
    pass

class GLPINotFoundError(GLPIException):
    """Exception raised when a resource is not found (404)."""
    pass

class GLPIBadRequestError(GLPIException):
    """Exception raised for bad requests (400)."""
    pass

class TicketResponse(BaseModel):
    """Pydantic model representing a GLPI Ticket response."""
    id: int
    name: str
    content: Optional[str] = None
    status: int
    
class FollowupRequest(BaseModel):
    """Pydantic model representing a request to add a followup."""
    items_id: int
    itemtype: str = "Ticket"
    content: str
    is_private: int = 0

class GLPIClient:
    """Client to interact with the GLPI API."""
    
    def __init__(self, base_url: str, app_token: str, user_token: str):
        self.base_url = base_url.rstrip("/")
        self.app_token = app_token
        self.user_token = user_token
        self.session_token: Optional[str] = None
        
        # Guardrail: Configure httpx client with required App-Token header
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "App-Token": self.app_token,
                "Content-Type": "application/json"
            }
        )

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        """Handles standard HTTP error statuses for GLPI."""
        if response.status_code == 400:
            raise GLPIBadRequestError(f"Bad Request: {response.text}")
        elif response.status_code == 401:
            raise GLPIAuthError(f"Unauthorized: {response.text}")
        elif response.status_code == 404:
            raise GLPINotFoundError(f"Not Found: {response.text}")
            
        response.raise_for_status()
        return response

    def _get_auth_headers(self) -> Dict[str, str]:
        """Returns headers required for authenticated requests, including guardrails."""
        if not self.session_token:
            raise GLPIAuthError("Session not initialized. Call init_session first.")
        
        return {
            "Session-Token": self.session_token,
            # Guardrail: Explicitly disable GLPI sanitization to avoid unexpected parsing (Prompt Injection Protection)
            "X-GLPI-Sanitized-Content": "false"
        }

    def init_session(self) -> str:
        """Initializes a session and retrieves the Session-Token."""
        headers = {
            "Authorization": f"user_token {self.user_token}"
        }
        response = self.client.get("/apirest.php/initSession", headers=headers)
        self._handle_response(response)
        
        data = response.json()
        self.session_token = data.get("session_token")
        
        if not self.session_token:
            raise GLPIAuthError("Failed to retrieve session_token from GLPI response")
            
        return self.session_token

    def get_ticket(self, ticket_id: int) -> TicketResponse:
        """Fetches a ticket and parses it into a structured Pydantic model."""
        headers = self._get_auth_headers()
        response = self.client.get(f"/apirest.php/Ticket/{ticket_id}", headers=headers)
        self._handle_response(response)
        
        return TicketResponse(**response.json())

    def add_followup(self, ticket_id: int, content: str) -> Dict[str, Any]:
        """Adds a followup (interaction) to a ticket."""
        headers = self._get_auth_headers()
        
        # Pydantic validation before sending
        payload = FollowupRequest(items_id=ticket_id, content=content).model_dump()
        
        response = self.client.post("/apirest.php/ITILFollowup", headers=headers, json={"input": payload})
        self._handle_response(response)
        
        return response.json()

    def kill_session(self) -> None:
        """Terminates the active GLPI session."""
        if not self.session_token:
            return
            
        headers = self._get_auth_headers()
        response = self.client.get("/apirest.php/killSession", headers=headers)
        self._handle_response(response)
        self.session_token = None
