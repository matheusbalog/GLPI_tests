import html
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field
from tools.glpi_tools import TicketResponse

class TicketClassification(BaseModel):
    """Classificacao estruturada do chamado."""
    category: Literal["BUG", "FEATURE_REQUEST", "SUPPORT_QUESTION", "UNCLEAR"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str

class IntakeResult(BaseModel):
    """Resultado da ingestao do chamado pelo Intake Agent."""
    ticket_id: int
    raw_title: str
    sanitized_content: str
    classification: TicketClassification
    next_state: Literal["CODE_ANALYSIS", "WAITING_CUSTOMER", "CLASSIFYING", "ESCALATED"]

class IntakeAgent:
    """Agente responsavel pela ingestao, isolamento de dados e classificacao inicial."""

    def sanitize_input(self, text: Optional[str]) -> str:
        if not text:
            return ""
        # Remove tags HTML perigosas mantendo o texto bruto seguro
        clean_text = html.escape(text.strip())
        return clean_text

    def classify(self, title: str, content: str) -> TicketClassification:
        combined_text = f"{title} {content}".lower()
        
        # Inspecao deterministica contra padroes obvios de Prompt Injection
        injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"system\s+prompt",
            r"approve\s+jira",
            r"override\s+guardrails"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, combined_text):
                return TicketClassification(
                    category="UNCLEAR",
                    confidence=0.1,
                    summary="Potential adversarial input detected. Marked for clarification/escalation."
                )

        # Heuristica deterministica de classificacao inicial
        bug_keywords = ["erro", "error", "falha", "exception", "500", "404", "bug", "crash", "quebrado"]
        unclear_keywords = ["me ajuda", "nao funciona nada", "urgente", "socorro", "ajuda"]

        if any(kw in combined_text for kw in unclear_keywords) and len(content.split()) < 8:
            return TicketClassification(
                category="UNCLEAR",
                confidence=0.4,
                summary="Informacoes insuficientes para analise tecnica."
            )

        if any(kw in combined_text for kw in bug_keywords):
            return TicketClassification(
                category="BUG",
                confidence=0.85,
                summary="Relato identificado como falha ou anomalia tecnica no sistema."
            )

        return TicketClassification(
            category="SUPPORT_QUESTION",
            confidence=0.6,
            summary="Duvida operacional ou solicitacao geral."
        )

    def process_ticket(self, ticket: TicketResponse) -> IntakeResult:
        sanitized_content = self.sanitize_input(ticket.content)
        classification = self.classify(ticket.name, sanitized_content)

        # Transicao de estado orientada por confianca e categoria
        if classification.category == "BUG" and classification.confidence >= 0.7:
            next_state = "CODE_ANALYSIS"
        elif classification.category == "UNCLEAR" or classification.confidence < 0.7:
            next_state = "WAITING_CUSTOMER"
        else:
            next_state = "CLASSIFYING"

        return IntakeResult(
            ticket_id=ticket.id,
            raw_title=ticket.name,
            sanitized_content=sanitized_content,
            classification=classification,
            next_state=next_state
        )
