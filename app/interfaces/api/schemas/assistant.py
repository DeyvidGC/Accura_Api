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
    DUPLICADOS = "Duplicados"


DEPENDENCY_TYPE_HEADERS: dict[str, tuple[str, ...]] = {
    "texto": ("Longitud minima", "Longitud maxima"),
    "numero": ("Valor mínimo", "Valor máximo", "Número de decimales"),
    "documento": ("Longitud minima", "Longitud maxima"),
    "lista": ("Lista",),
    "lista compleja": ("Lista compleja",),
    "telefono": ("Longitud minima", "Código de país"),
    "correo": ("Formato", "Longitud máxima"),
    "fecha": ("Formato", "Fecha mínima", "Fecha máxima"),
}


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
    header_rule: list[str] = Field(
        ...,
        alias="Header rule",
        min_length=1,
        description="Encabezados que intervienen en la validación",
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

        if not isinstance(self.header_rule, list) or not self.header_rule:
            raise ValueError(
                "El campo 'Header rule' debe ser una lista con al menos un elemento."
            )
        for item in self.header_rule:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    "Cada elemento dentro de 'Header rule' debe ser una cadena no vacía."
                )

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

        def ensure_non_empty_str(name: str) -> None:
            value = regla.get(name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"'{name}' debe ser una cadena no vacía.")

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
            ensure_keys({"Formato", "Fecha mínima", "Fecha máxima"})
            ensure_non_empty_str("Formato")
            ensure_non_empty_str("Fecha mínima")
            ensure_non_empty_str("Fecha máxima")
            formato = regla.get("Formato")
            formatos_validos = {"yyyy-MM-dd", "dd/MM/yyyy", "MM-dd-yyyy"}
            if formato not in formatos_validos:
                raise ValueError(
                    "El formato de fecha debe ser uno de: " + ", ".join(sorted(formatos_validos))
                )

        elif tipo == TipoDatoEnum.DEPENDENCIA:
            ensure_keys({"reglas especifica"})
            reglas_especifica = regla.get("reglas especifica")
            if not isinstance(reglas_especifica, list) or not reglas_especifica:
                raise ValueError("'reglas especifica' debe ser una lista con al menos un elemento.")

            allowed_types = set(DEPENDENCY_TYPE_HEADERS.keys())

            def ensure_config_exact_keys(config: dict[str, Any], expected: set[str], type_label: str) -> None:
                keys = set(config.keys())
                if keys != expected:
                    raise ValueError(
                        "La configuración para '"
                        + type_label
                        + "' debe contener exactamente las claves: "
                        + ", ".join(sorted(expected))
                    )

            def ensure_config_int_value(
                config: dict[str, Any], key: str, *, minimum: int | None, type_label: str
            ) -> None:
                value = config.get(key)
                if not isinstance(value, int):
                    raise ValueError(
                        f"'{key}' en la configuración de '{type_label}' debe ser un número entero."
                    )
                if minimum is not None and value < minimum:
                    raise ValueError(
                        f"'{key}' en la configuración de '{type_label}' debe ser mayor o igual a {minimum}."
                    )

            def ensure_config_numeric(
                value: Any, key: str, type_label: str, *, allow_none: bool = False
            ) -> None:
                if value is None and allow_none:
                    return
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"'{key}' en la configuración de '{type_label}' debe ser numérico."
                    )

            dependent_label_reference: str | None = None
            normalized_dependent_reference: str | None = None
            expected_headers: set[str] = set()

            for entrada in reglas_especifica:
                if not isinstance(entrada, dict) or len(entrada) < 2:
                    raise ValueError(
                        "Cada elemento de 'reglas especifica' debe ser un objeto con al menos dos claves."
                    )

                dependent_labels: list[str] = []
                type_label_seen: str | None = None

                for clave, contenido in entrada.items():
                    if not isinstance(clave, str) or not clave.strip():
                        raise ValueError(
                            "Cada clave dentro de 'reglas especifica' debe ser una cadena no vacía."
                        )
                    normalized_clave = _normalize_label(clave)

                    if normalized_clave in allowed_types:
                        if type_label_seen is not None:
                            raise ValueError(
                                "Cada elemento de 'reglas especifica' debe definir un único tipo de dato."
                            )
                        type_label_seen = normalized_clave
                        if not isinstance(contenido, dict):
                            raise ValueError(
                                f"La configuración asociada a '{clave}' debe ser un objeto."
                            )

                        if normalized_clave == "texto":
                            ensure_config_exact_keys(
                                contenido, {"Longitud minima", "Longitud maxima"}, clave
                            )
                            ensure_config_int_value(
                                contenido, "Longitud minima", minimum=0, type_label=clave
                            )
                            ensure_config_int_value(
                                contenido, "Longitud maxima", minimum=0, type_label=clave
                            )
                        elif normalized_clave == "numero":
                            ensure_config_exact_keys(
                                contenido,
                                {"Valor mínimo", "Valor máximo", "Número de decimales"},
                                clave,
                            )
                            ensure_config_numeric(
                                contenido.get("Valor mínimo"), "Valor mínimo", clave, allow_none=True
                            )
                            ensure_config_numeric(
                                contenido.get("Valor máximo"), "Valor máximo", clave, allow_none=True
                            )
                            ensure_config_int_value(
                                contenido, "Número de decimales", minimum=0, type_label=clave
                            )
                        elif normalized_clave == "documento":
                            ensure_config_exact_keys(
                                contenido, {"Longitud minima", "Longitud maxima"}, clave
                            )
                            ensure_config_int_value(
                                contenido, "Longitud minima", minimum=1, type_label=clave
                            )
                            ensure_config_int_value(
                                contenido, "Longitud maxima", minimum=1, type_label=clave
                            )
                        elif normalized_clave == "lista":
                            ensure_config_exact_keys(contenido, {"Lista"}, clave)
                            valores = contenido.get("Lista")
                            if not isinstance(valores, list) or not valores:
                                raise ValueError(
                                    f"'Lista' en la configuración de '{clave}' debe ser una lista con al menos un elemento."
                                )
                            for elemento in valores:
                                if not isinstance(elemento, str) or not elemento.strip():
                                    raise ValueError(
                                        "Cada valor dentro de 'Lista' debe ser una cadena no vacía."
                                    )
                        elif normalized_clave == "lista compleja":
                            ensure_config_exact_keys(contenido, {"Lista compleja"}, clave)
                            combinaciones = contenido.get("Lista compleja")
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
                        elif normalized_clave == "telefono":
                            ensure_config_exact_keys(
                                contenido, {"Longitud minima", "Código de país"}, clave
                            )
                            ensure_config_int_value(
                                contenido, "Longitud minima", minimum=1, type_label=clave
                            )
                            codigo = contenido.get("Código de país")
                            if not isinstance(codigo, str) or not re.fullmatch(r"^\+\d{1,3}$", codigo):
                                raise ValueError(
                                    "'Código de país' debe cumplir el patrón +<código numérico> de 1 a 3 dígitos."
                                )
                        elif normalized_clave == "correo":
                            ensure_config_exact_keys(
                                contenido, {"Formato", "Longitud máxima"}, clave
                            )
                            formato = contenido.get("Formato")
                            if not isinstance(formato, str) or not formato.strip():
                                raise ValueError("'Formato' debe ser una cadena no vacía.")
                            ensure_config_int_value(
                                contenido, "Longitud máxima", minimum=1, type_label=clave
                            )
                        elif normalized_clave == "fecha":
                            ensure_config_exact_keys(
                                contenido, {"Formato", "Fecha mínima", "Fecha máxima"}, clave
                            )
                            formato = contenido.get("Formato")
                            formatos_validos = {"yyyy-MM-dd", "dd/MM/yyyy", "MM-dd-yyyy"}
                            if formato not in formatos_validos:
                                raise ValueError(
                                    "El formato de fecha debe ser uno de: "
                                    + ", ".join(sorted(formatos_validos))
                                )
                            for etiqueta in ("Fecha mínima", "Fecha máxima"):
                                valor = contenido.get(etiqueta)
                                if not isinstance(valor, str) or not valor.strip():
                                    raise ValueError(
                                        f"'{etiqueta}' en la configuración de '{clave}' debe ser una cadena no vacía."
                                    )

                        expected_headers.update(DEPENDENCY_TYPE_HEADERS[normalized_clave])
                        continue

                    if isinstance(contenido, dict):
                        raise ValueError(
                            "El valor asociado al campo dependiente no puede ser un objeto."
                        )
                    dependent_labels.append(clave)

                if type_label_seen is None:
                    raise ValueError(
                        "Cada regla dependiente debe incluir al menos una configuración de tipo soportado."
                    )

                if not dependent_labels:
                    raise ValueError(
                        "Cada regla dependiente debe indicar el encabezado dependiente y su valor."
                    )

                if len(dependent_labels) > 1:
                    raise ValueError(
                        "Cada regla dependiente debe especificar un único campo dependiente."
                    )

                dependent_label = dependent_labels[0]
                normalized_dependent = _normalize_label(dependent_label)

                if dependent_label_reference is None:
                    dependent_label_reference = dependent_label
                    normalized_dependent_reference = normalized_dependent
                elif normalized_dependent_reference != normalized_dependent:
                    raise ValueError(
                        "Todas las reglas dependientes deben usar el mismo encabezado dependiente."
                    )

            if dependent_label_reference is None:
                raise ValueError(
                    "No se pudo identificar el campo dependiente dentro de 'reglas especifica'."
                )

            expected_headers.add(dependent_label_reference)
            normalized_header_values = {_normalize_label(item) for item in self.header}
            missing_headers = [
                label
                for label in expected_headers
                if _normalize_label(label) not in normalized_header_values
            ]
            if missing_headers:
                raise ValueError(
                    "El header debe incluir los siguientes campos para la regla dependiente: "
                    + ", ".join(sorted(missing_headers))
                )

        elif tipo == TipoDatoEnum.DUPLICADOS:
            candidate_keys = ("Campos", "Columnas", "Fields", "fields")
            extracted_fields: list[str] = []

            for key in candidate_keys:
                raw_fields = regla.get(key)
                if raw_fields is None:
                    continue
                if not isinstance(raw_fields, list) or not raw_fields:
                    raise ValueError(
                        f"'{key}' debe ser una lista con al menos un elemento."
                    )

                normalized_fields: list[str] = []
                for field in raw_fields:
                    if not isinstance(field, str) or not field.strip():
                        raise ValueError(
                            "Cada elemento definido en la lista de campos debe ser una cadena no vacía."
                        )
                    normalized_fields.append(field.strip())

                if normalized_fields:
                    extracted_fields.extend(normalized_fields)
                    break

            if not extracted_fields:
                raise ValueError(
                    "La configuración para la regla de duplicados debe incluir al menos un listado de campos."
                )

            allowed_booleans = (
                "Ignorar vacios",
                "Ignorar vacíos",
                "Ignorar vacias",
                "Ignorar vacías",
                "Ignore empty",
                "Ignore empties",
            )
            for flag in allowed_booleans:
                value = regla.get(flag)
                if value is None:
                    continue
                if not isinstance(value, bool):
                    raise ValueError(f"'{flag}' debe ser un valor booleano.")

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
