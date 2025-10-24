"""Pydantic models for the assistant interaction endpoints."""

from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    """Payload with the user's free-form message."""

    message: str = Field(..., min_length=1, description="Mensaje que será analizado por el asistente")


class ResponseGuidance(BaseModel):
    """Guidelines that describe how the assistant should craft its answer."""

    allowed_topics: list[str] = Field(
        ..., description="Temas permitidos o recomendados para la respuesta del asistente"
    )
    tone: str = Field(..., description="Tono sugerido para responder al usuario")
    formatting: str = Field(
        ..., description="Formato recomendado (por ejemplo, viñetas, pasos, párrafos cortos, etc.)"
    )
    helpful_phrases: list[str] = Field(
        default_factory=list,
        description="Frases útiles que se pueden emplear en la respuesta",
    )


class AssistantMessageResponse(BaseModel):
    """Structured response generated from the LLM output."""

    summary: str = Field(
        ..., description="Resumen conciso en español sobre la intención principal del usuario"
    )
    user_needs: list[str] = Field(
        ..., description="Elementos concretos que el usuario está solicitando o necesita"
    )
    response_guidance: ResponseGuidance = Field(
        ..., description="Instrucciones sobre cómo debe responder el asistente"
    )
    suggested_reply: str = Field(
        ..., description="Ejemplo de respuesta final siguiendo las indicaciones de la guía"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Preguntas adicionales para profundizar en la necesidad del usuario",
    )
