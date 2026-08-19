import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

load_dotenv()

from tools.glpi_tools import (
    GLPIClient,
    GLPIException,
    GLPIAuthError,
    GLPINotFoundError,
    GLPIBadRequestError,
    TicketResponse,
    FollowupResponse,
    SolutionResponse,
)
from agents.intake_agent import IntakeAgent, IntakeResult

app = FastAPI(
    title="Workflow Autonomo GLPI 10.0.5 - API de Validacao",
    version="1.0.0",
    description="API para testes de integracao, consumo e validacao de endpoints do GLPI 10.0.5."
)

intake_agent = IntakeAgent()

def get_glpi_client() -> GLPIClient:
    base_url = os.getenv("GLPI_BASE_URL", "http://glpi:80/apirest.php")
    app_token = os.getenv("GLPI_APP_TOKEN", "")
    user_token = os.getenv("GLPI_USER_TOKEN", "")
    return GLPIClient(base_url=base_url, app_token=app_token, user_token=user_token)

class ConnectionResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None

class FollowupInput(BaseModel):
    content: str
    is_private: int = 0

class StatusUpdateInput(BaseModel):
    status: int = Field(..., description="Novo status do chamado (ex: 1=New, 2=Assigned, 4=Pending, 5=Solved, 6=Closed)")

class SolutionInput(BaseModel):
    content: str

@app.get("/health", tags=["Infraestrutura"])
def health_check():
    return {"status": "healthy", "service": "workflow-core", "target_glpi_version": "10.0.5"}

@app.post("/glpi/test-connection", response_model=ConnectionResponse, tags=["GLPI - Conectividade"])
def test_connection():
    """Valida ciclo completo de sessao (initSession -> killSession) no GLPI configurado."""
    try:
        with get_glpi_client() as client:
            token = client.session_token
        return ConnectionResponse(
            success=True,
            message="Conexao com GLPI 10.0.5 validada com sucesso.",
            session_token=token
        )
    except GLPIAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro de autenticacao: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falha de conexao: {str(e)}")

@app.get("/glpi/ticket/{ticket_id}", response_model=TicketResponse, tags=["GLPI - Tickets"])
def get_ticket(ticket_id: int):
    """Consulta dados de um chamado por ID."""
    with get_glpi_client() as client:
        try:
            return client.get_ticket(ticket_id)
        except GLPINotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} nao encontrado.")
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/glpi/ticket/{ticket_id}/followups", response_model=List[FollowupResponse], tags=["GLPI - Tickets"])
def get_followups(ticket_id: int):
    """Consulta historico de followups de um chamado."""
    with get_glpi_client() as client:
        try:
            return client.get_followups(ticket_id)
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/glpi/ticket/{ticket_id}/followup", tags=["GLPI - Interacoes"])
def add_followup(ticket_id: int, payload: FollowupInput):
    """Adiciona mensagem/interacao a um chamado."""
    with get_glpi_client() as client:
        try:
            return client.add_followup(ticket_id, content=payload.content, is_private=payload.is_private)
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.patch("/glpi/ticket/{ticket_id}/status", tags=["GLPI - Tickets"])
def update_status(ticket_id: int, payload: StatusUpdateInput):
    """Atualiza o status de um chamado."""
    with get_glpi_client() as client:
        try:
            return client.update_ticket_status(ticket_id, status=payload.status)
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/glpi/ticket/{ticket_id}/solution", response_model=SolutionResponse, tags=["GLPI - Resolucao"])
def add_solution(ticket_id: int, payload: SolutionInput):
    """Adiciona solucao tecnica ao chamado."""
    with get_glpi_client() as client:
        try:
            return client.add_solution(ticket_id, content=payload.content)
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/glpi/ticket/{ticket_id}/intake", response_model=IntakeResult, tags=["Agentes - Triagem"])
def run_intake(ticket_id: int):
    """Executa ingestao, sanitizacao e classificacao inicial de um chamado."""
    with get_glpi_client() as client:
        try:
            ticket = client.get_ticket(ticket_id)
        except GLPINotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} nao encontrado.")
        except GLPIException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            
    return intake_agent.process_ticket(ticket)
