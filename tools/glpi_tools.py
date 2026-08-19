from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

class GLPIException(Exception):
    """Excecao base para operacoes no GLPI."""
    pass

class GLPIAuthError(GLPIException):
    """Erro de autenticacao ou sessao invalida (401)."""
    pass

class GLPINotFoundError(GLPIException):
    """Recurso nao encontrado (404)."""
    pass

class GLPIBadRequestError(GLPIException):
    """Requisicao invalida ou parametros incorretos (400)."""
    pass

class TicketResponse(BaseModel):
    """Estrutura de dados de retorno de Ticket no GLPI 10.0.5."""
    id: int
    name: str
    content: Optional[str] = None
    status: int

class FollowupRequest(BaseModel):
    """Payload para criacao de Followup."""
    items_id: int
    itemtype: str = "Ticket"
    content: str
    is_private: int = 0

class FollowupResponse(BaseModel):
    """Estrutura de leitura de Followup."""
    id: int
    items_id: int
    content: Optional[str] = None
    is_private: Optional[int] = 0

class SolutionRequest(BaseModel):
    """Payload para adicao de Solucao."""
    items_id: int
    itemtype: str = "Ticket"
    content: str
    status: int = 2  # 2: Solved

class SolutionResponse(BaseModel):
    """Estrutura de retorno para Solucao."""
    id: int
    message: Optional[str] = None

class GLPIClient:
    """Cliente HTTP com tipagem e guardrails para API REST do GLPI 10.0.5."""

    def __init__(self, base_url: str, app_token: str, user_token: str):
        cleaned_url = base_url.rstrip("/")
        if cleaned_url.endswith("/apirest.php"):
            cleaned_url = cleaned_url[:-len("/apirest.php")].rstrip("/")
        self.base_url = cleaned_url
        self.app_token = app_token
        self.user_token = user_token
        self.session_token: Optional[str] = None
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "App-Token": self.app_token,
                "Content-Type": "application/json",
            },
        )

    def __enter__(self) -> "GLPIClient":
        self.init_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.kill_session()
        self.client.close()

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        if response.status_code == 400:
            raise GLPIBadRequestError(f"Bad Request: {response.text}")
        if response.status_code == 401:
            raise GLPIAuthError(f"Unauthorized: {response.text}")
        if response.status_code == 404:
            raise GLPINotFoundError(f"Not Found: {response.text}")
        response.raise_for_status()
        return response

    def _get_auth_headers(self) -> Dict[str, str]:
        if not self.session_token:
            raise GLPIAuthError("Sessao nao inicializada. Execute init_session primeiro.")
        return {
            "Session-Token": self.session_token,
            "X-GLPI-Sanitized-Content": "false",
        }

    def init_session(self) -> str:
        headers = {"Authorization": f"user_token {self.user_token}"}
        response = self.client.get("/apirest.php/initSession", headers=headers)
        self._handle_response(response)
        data = response.json()
        self.session_token = data.get("session_token")
        if not self.session_token:
            raise GLPIAuthError("session_token ausente na resposta do GLPI")
        return self.session_token

    def get_ticket(self, ticket_id: int) -> TicketResponse:
        headers = self._get_auth_headers()
        response = self.client.get(f"/apirest.php/Ticket/{ticket_id}", headers=headers)
        self._handle_response(response)
        return TicketResponse(**response.json())

    def get_followups(self, ticket_id: int) -> List[FollowupResponse]:
        headers = self._get_auth_headers()
        response = self.client.get(f"/apirest.php/Ticket/{ticket_id}/ITILFollowup", headers=headers)
        self._handle_response(response)
        raw_data = response.json()
        if isinstance(raw_data, list):
            return [FollowupResponse(**item) for item in raw_data]
        return []

    def add_followup(self, ticket_id: int, content: str, is_private: int = 0) -> Dict[str, Any]:
        headers = self._get_auth_headers()
        payload = FollowupRequest(items_id=ticket_id, content=content, is_private=is_private).model_dump()
        response = self.client.post("/apirest.php/ITILFollowup", headers=headers, json={"input": payload})
        self._handle_response(response)
        return response.json()

    def update_ticket_status(self, ticket_id: int, status: int) -> Dict[str, Any]:
        headers = self._get_auth_headers()
        payload = {"id": ticket_id, "status": status}
        response = self.client.put(f"/apirest.php/Ticket/{ticket_id}", headers=headers, json={"input": payload})
        self._handle_response(response)
        return response.json()

    def add_solution(self, ticket_id: int, content: str) -> SolutionResponse:
        headers = self._get_auth_headers()
        payload = SolutionRequest(items_id=ticket_id, content=content).model_dump()
        response = self.client.post("/apirest.php/ITILSolution", headers=headers, json={"input": payload})
        self._handle_response(response)
        return SolutionResponse(**response.json())

    def kill_session(self) -> None:
        if not self.session_token:
            return
        headers = self._get_auth_headers()
        response = self.client.get("/apirest.php/killSession", headers=headers)
        self._handle_response(response)
        self.session_token = None
