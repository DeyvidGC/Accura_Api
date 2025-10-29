"""Pydantic models for the assistant interaction endpoints."""

from __future__ import annotations

import re
import unicodedata
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
    LISTA_COMPLEJA = "Lista compleja"
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
    campo_obligatorio: bool = Field(
        ..., alias="Campo obligatorio", description="Indica si el campo es obligatorio"
    )
    mensaje_de_error: str = Field(
        ..., alias="Mensaje de error", description="Mensaje que se muestra cuando la validación falla"
    )
    descripcion: str = Field(..., alias="Descripción", description="Descripción detallada de la regla")
    ejemplo: Any = Field(..., alias="Ejemplo", description="Ejemplo representativo que cumple la regla")
    header: list[str] = Field(
        ..., alias="Header", min_length=1, description="Campos disponibles dentro de la regla"
    )
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

        if not isinstance(self.header, list) or not self.header:
            raise ValueError("El campo 'Header' debe ser una lista con al menos un elemento.")
        for item in self.header:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Cada elemento dentro de 'Header' debe ser una cadena no vacía.")

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

        elif tipo == TipoDatoEnum.LISTA_COMPLEJA:
            ensure_keys({"Lista compleja"})
            combinaciones = regla.get("Lista compleja")
            if not isinstance(combinaciones, list) or not combinaciones:
                raise ValueError(
                    "'Lista compleja' debe ser una lista con al menos una combinación permitida."
                )
            for combinacion in combinaciones:
                if not isinstance(combinacion, dict) or not combinacion:
                    raise ValueError(
                        "Cada combinación en 'Lista compleja' debe ser un objeto con al menos una clave."
                    )
                for campo, valor in combinacion.items():
                    if not isinstance(campo, str) or not campo.strip():
                        raise ValueError(
                            "Las claves de cada combinación deben ser cadenas no vacías."
                        )
                    if isinstance(valor, str):
                        if not valor.strip():
                            raise ValueError(
                                "Los valores de cada combinación deben ser cadenas o números no vacíos."
                            )
                        continue
                    if not isinstance(valor, (int, float)):
                        raise ValueError(
                            "Los valores de cada combinación deben ser cadenas o números no vacíos."
                        )
                    if isinstance(valor, float) and valor != valor:
                        raise ValueError(
                            "Los valores de cada combinación no pueden ser NaN."
                        )

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
            ensure_keys({"Nombre dependiente", "reglas especifica"})
            nombre_dependiente = regla.get("Nombre dependiente")
            if not isinstance(nombre_dependiente, str) or not nombre_dependiente.strip():
                raise ValueError("'Nombre dependiente' debe ser una cadena no vacía.")
            reglas_especifica = regla.get("reglas especifica")
            if not isinstance(reglas_especifica, list) or not reglas_especifica:
                raise ValueError("'reglas especifica' debe ser una lista con al menos un elemento.")

            normalized_dependiente = _normalize_label(nombre_dependiente)

            for entrada in reglas_especifica:
                if not isinstance(entrada, dict) or len(entrada) < 2:
                    raise ValueError(
                        "Cada elemento de 'reglas especifica' debe ser un objeto con al menos dos claves."
                    )

                dependent_key_found = False

                for clave, contenido in entrada.items():
                    if not isinstance(clave, str) or not clave.strip():
                        raise ValueError(
                            "Cada clave dentro de 'reglas especifica' debe ser una cadena no vacía."
                        )
                    normalized_clave = _normalize_label(clave)

                    if normalized_clave == normalized_dependiente:
                        dependent_key_found = True
                        if isinstance(contenido, dict):
                            raise ValueError(
                                "El valor asociado al campo dependiente no puede ser un objeto."
                            )
                        continue

                    if normalized_clave not in {
                        "texto",
                        "numero",
                        "documento",
                        "lista",
                        "lista compleja",
                        "telefono",
                        "correo",
                        "fecha",
                    }:
                        raise ValueError(
                            "Las configuraciones dependientes solo pueden incluir tipos soportados (Texto, Número, Documento, Lista, Lista compleja, Telefono, Correo o Fecha)."
                        )
                    if not isinstance(contenido, dict):
                        raise ValueError(
                            "La configuración asociada a cada tipo dependiente debe ser un objeto."
                        )

                if not dependent_key_found:
                    raise ValueError(
                        "Cada regla dependiente debe indicar el valor del campo especificado en 'Nombre dependiente'."
                    )

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


def _normalize_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower().strip()
