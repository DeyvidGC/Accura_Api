"""Pydantic models for the assistant interaction endpoints."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssistantMessageRequest(BaseModel):
    """Payload with the user's free-form message."""

    message: str = Field(..., min_length=1, description="Mensaje que será analizado por el asistente")


class TipoDatoEnum(str, Enum):
    """Enumeración para los tipos de dato soportados en la regla."""

    TEXTO = "Texto"
    NUMERO = "Número"
    DOCUMENTO = "Documento"
    LISTA = "Lista"
    TELEFONO = "Telefono"
    CORREO = "Correo"
    FECHA = "Fecha"
    DEPENDENCIA = "Dependencia"
    VALIDACION_CONJUNTA = "Validación conjunta"


class AssistantMessageResponse(BaseModel):
    """Structured response describing a single validation rule."""

    nombre_de_la_regla: str = Field(
        ..., alias="Nombre de la regla", min_length=1, description="Nombre identificador de la regla"
    )
    tipo_de_dato: TipoDatoEnum = Field(..., alias="Tipo de dato", description="Tipo de dato que valida la regla")
    campo_obligatorio: bool = Field(..., alias="Campo obligatorio", description="Indica si el campo es obligatorio")
    mensaje_de_error: str = Field(..., alias="Mensaje de error", description="Mensaje que se muestra cuando la validación falla")
    descripcion: str = Field(..., alias="Descripción", description="Descripción detallada de la regla")
    ejemplo: Any = Field(..., alias="Ejemplo", description="Ejemplo representativo que cumple la regla")
    regla: dict[str, Any] = Field(
        ..., alias="Regla", description="Configuración específica de la regla según el tipo de dato"
    )

    model_config = ConfigDict(
        validate_by_name=True,
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_regla(self) -> "AssistantMessageResponse":
        tipo: TipoDatoEnum | None = self.tipo_de_dato
        regla: Any = self.regla

        if not isinstance(regla, dict):
            raise ValueError("El campo 'Regla' debe ser un objeto JSON.")

        def ensure_keys(expected_keys: set[str], allow_extra: bool = False) -> None:
            keys = set(regla.keys())
            if allow_extra:
                if not expected_keys.issubset(keys):
                    faltantes = expected_keys - keys
                    raise ValueError(
                        "La regla debe incluir las claves: " + ", ".join(sorted(faltantes))
                    )
                return
            if keys != expected_keys:
                raise ValueError(
                    "La regla debe contener exactamente las claves: " + ", ".join(sorted(expected_keys))
                )

        def ensure_int(name: str, minimum: int | None = None) -> None:
            value = regla.get(name)
            if not isinstance(value, int):
                raise ValueError(f"'{name}' debe ser un número entero.")
            if minimum is not None and value < minimum:
                raise ValueError(f"'{name}' debe ser mayor o igual a {minimum}.")

        def ensure_number(value: Any, allow_none: bool = False) -> None:
            if value is None and allow_none:
                return
            if not isinstance(value, (int, float)):
                raise ValueError("Los límites deben ser numéricos o nulos.")

        if tipo == TipoDatoEnum.TEXTO:
            ensure_keys({"Longitud minima", "Longitud maxima"})
            ensure_int("Longitud minima", minimum=0)
            ensure_int("Longitud maxima", minimum=0)

        elif tipo == TipoDatoEnum.NUMERO:
            ensure_keys({"Valor mínimo", "Valor máximo", "Número de decimales"})
            ensure_number(regla.get("Valor mínimo"), allow_none=True)
            ensure_number(regla.get("Valor máximo"), allow_none=True)
            ensure_int("Número de decimales", minimum=0)

        elif tipo == TipoDatoEnum.DOCUMENTO:
            ensure_keys({"Longitud minima", "Longitud maxima"})
            ensure_int("Longitud minima", minimum=1)
            ensure_int("Longitud maxima", minimum=1)

        elif tipo == TipoDatoEnum.LISTA:
            if not isinstance(regla, dict):  # pragma: no cover - defensive
                raise ValueError("La regla de tipo 'Lista' debe ser un objeto JSON.")

        elif tipo == TipoDatoEnum.TELEFONO:
            ensure_keys({"Longitud minima", "Código de país"})
            ensure_int("Longitud minima", minimum=1)
            codigo = regla.get("Código de país")
            if not isinstance(codigo, str) or not re.fullmatch(r"^\+\d{1,3}$", codigo):
                raise ValueError("'Código de país' debe cumplir el patrón +<código numérico> de 1 a 3 dígitos.")

        elif tipo == TipoDatoEnum.CORREO:
            ensure_keys({"Formato", "Longitud máxima"})
            if not isinstance(regla.get("Formato"), str) or not regla["Formato"].strip():
                raise ValueError("'Formato' debe ser una cadena no vacía.")
            ensure_int("Longitud máxima", minimum=1)

        elif tipo == TipoDatoEnum.FECHA:
            ensure_keys({"Formato"})
            formato = regla.get("Formato")
            formatos_validos = {"yyyy-MM-dd", "dd/MM/yyyy", "MM-dd-yyyy"}
            if formato not in formatos_validos:
                raise ValueError(
                    "El formato de fecha debe ser uno de: " + ", ".join(sorted(formatos_validos))
                )

        elif tipo == TipoDatoEnum.DEPENDENCIA:
            ensure_keys({"Nombre dependiente", "valor", "reglas especifica"})
            nombre_dependiente = regla.get("Nombre dependiente")
            if not isinstance(nombre_dependiente, str) or not nombre_dependiente.strip():
                raise ValueError("'Nombre dependiente' debe ser una cadena no vacía.")
            reglas_especifica = regla.get("reglas especifica")
            if not isinstance(reglas_especifica, list) or not reglas_especifica:
                raise ValueError("'reglas especifica' debe ser una lista con al menos un elemento.")

            for entrada in reglas_especifica:
                if not isinstance(entrada, dict) or len(entrada) != 1:
                    raise ValueError(
                        "Cada elemento de 'reglas especifica' debe ser un objeto con una única clave ('Texto' o 'Número')."
                    )
                clave, contenido = next(iter(entrada.items()))
                if clave == "Texto":
                    if not isinstance(contenido, dict):
                        raise ValueError("La configuración de 'Texto' debe ser un objeto.")
                    claves_texto = {"Longitud minima", "Longitud maxima"}
                    if set(contenido.keys()) != claves_texto:
                        raise ValueError("La regla de 'Texto' debe incluir 'Longitud minima' y 'Longitud maxima'.")
                    for campo in claves_texto:
                        valor = contenido.get(campo)
                        if not isinstance(valor, int) or valor < 0:
                            raise ValueError("Los límites de longitud en 'Texto' deben ser enteros mayores o iguales a 0.")
                elif clave == "Número":
                    if not isinstance(contenido, dict):
                        raise ValueError("La configuración de 'Número' debe ser un objeto.")
                    claves_numero = {"Valor mínimo", "Valor máximo", "Número de decimales"}
                    if set(contenido.keys()) != claves_numero:
                        raise ValueError(
                            "La regla de 'Número' debe incluir 'Valor mínimo', 'Valor máximo' y 'Número de decimales'."
                        )
                    valor_min = contenido.get("Valor mínimo")
                    valor_max = contenido.get("Valor máximo")
                    if valor_min is not None and not isinstance(valor_min, (int, float)):
                        raise ValueError("'Valor mínimo' debe ser numérico o nulo.")
                    if valor_max is not None and not isinstance(valor_max, (int, float)):
                        raise ValueError("'Valor máximo' debe ser numérico o nulo.")
                    decimales = contenido.get("Número de decimales")
                    if not isinstance(decimales, int) or decimales < 0:
                        raise ValueError("'Número de decimales' debe ser un entero mayor o igual a 0.")
                else:
                    raise ValueError("Cada regla específica debe definirse bajo 'Texto' o 'Número'.")

        elif tipo == TipoDatoEnum.VALIDACION_CONJUNTA:
            ensure_keys({"Nombre de campos"})
            nombres = regla.get("Nombre de campos")
            if not isinstance(nombres, list) or not nombres:
                raise ValueError("'Nombre de campos' debe ser una lista con al menos un elemento.")
            for nombre in nombres:
                if not isinstance(nombre, str) or not nombre.strip():
                    raise ValueError("Cada nombre de campo debe ser una cadena no vacía.")

        else:  # pragma: no cover - defensive fallback
            raise ValueError("Tipo de dato no soportado para la validación de la regla.")

        return self
