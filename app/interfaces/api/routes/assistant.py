"""Rutas para interactuar con el asistente basado en OpenAI."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.rules import list_recent_rules as list_recent_rules_uc
from app.domain.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.openai_client import (
    OpenAIServiceError,
    StructuredChatService,
)
from app.interfaces.api.dependencies import (
    get_structured_chat_service,
    require_admin,
)
from app.interfaces.api.schemas import (
    AssistantMessageRequest,
    AssistantMessageResponse,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/analyze", response_model=AssistantMessageResponse)
def analyze_message(
    payload: AssistantMessageRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    assistant: StructuredChatService = Depends(get_structured_chat_service),
) -> AssistantMessageResponse:
    """Genera una respuesta estructurada que indica cómo atender el mensaje del usuario."""

    try:
        recent_rules = list_recent_rules_uc(db, limit=5)
        serialized_rules = [
            {
                "id": rule.id,
                "rule": rule.rule,
            }
            for rule in recent_rules
        ]
        raw_response = assistant.generate_structured_response(
            payload.message,
            recent_rules=serialized_rules or None,
        )
    except OpenAIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        if hasattr(AssistantMessageResponse, "model_validate"):
            return AssistantMessageResponse.model_validate(raw_response)
        return AssistantMessageResponse.parse_obj(raw_response)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive against schema drift
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="La respuesta recibida no coincide con el esquema esperado.",
        ) from exc
