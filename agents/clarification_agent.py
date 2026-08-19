from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from tools.glpi_tools import GLPIClient

MAX_CLARIFICATION_ROUNDS = 3

class ClarificationResult(BaseModel):
    """Resultado da operacao de solicitacao de esclarecimento."""
    ticket_id: int
    current_rounds: int
    question_text: str
    next_state: Literal["WAITING_CUSTOMER", "ESCALATED"]
    escalated: bool = False

class ClarificationAgent:
    """Agente encarregado de interagir com o usuario no GLPI para obter dados faltantes."""

    def __init__(self, glpi_client: GLPIClient):
        self.glpi_client = glpi_client

    def generate_question(self, missing_fields: List[str]) -> str:
        fields_str = ", ".join(missing_fields)
        return (
            "Prezado(a), para prosseguirmos com a analise tecnica do seu chamado, "
            f"precisamos das seguintes informacoes adicionais: {fields_str}. "
            "Por favor, responda diretamente a este chamado."
        )

    def request_clarification(
        self,
        ticket_id: int,
        current_rounds: int,
        missing_fields: Optional[List[str]] = None
    ) -> ClarificationResult:
        missing_fields = missing_fields or ["detalhes adicionais"]

        # Regra inviolavel: Maximo 3 rodadas antes do escalonamento compulsorio
        if current_rounds >= MAX_CLARIFICATION_ROUNDS:
            escalation_msg = (
                "O chamado atingiu o limite de tentativas de esclarecimento automatico (3 rodadas) "
                "sem obter as informacoes necessarias. O caso foi escalonado para intervencao humana."
            )
            self.glpi_client.add_followup(ticket_id, escalation_msg, is_private=0)
            
            return ClarificationResult(
                ticket_id=ticket_id,
                current_rounds=current_rounds,
                question_text=escalation_msg,
                next_state="ESCALATED",
                escalated=True
            )

        question = self.generate_question(missing_fields)
        self.glpi_client.add_followup(ticket_id, question, is_private=0)
        
        # Status 4 no GLPI = Pending (Aguardando solicitante)
        self.glpi_client.update_ticket_status(ticket_id, status=4)

        return ClarificationResult(
            ticket_id=ticket_id,
            current_rounds=current_rounds + 1,
            question_text=question,
            next_state="WAITING_CUSTOMER",
            escalated=False
        )
