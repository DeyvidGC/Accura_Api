"""Routes for interacting with the OpenAI powered assistant."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.openai_client import (
    OpenAIServiceError,
    StructuredChatService,
)
from app.interfaces.api.dependencies import get_structured_chat_service
from app.interfaces.api.schemas import (
    AssistantMessageRequest,
    AssistantMessageResponse,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/analyze", response_model=AssistantMessageResponse)
def analyze_message(
    payload: AssistantMessageRequest,
    assistant: StructuredChatService = Depends(get_structured_chat_service),
) -> AssistantMessageResponse:
    """Generate a structured reply describing how to respond to the user message."""

    try:
        raw_response = assistant.generate_structured_response(payload.message)
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
