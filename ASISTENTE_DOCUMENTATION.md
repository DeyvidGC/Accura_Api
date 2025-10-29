# Asistente Documentation

## Índice
- [Documento A. Flujo general del asistente](#documento-a-flujo-general-del-asistente)
  - [A.1 Solicitar reglas de validación existentes](#a1-solicitar-reglas-de-validación-existentes)
  - [A.2 Crear nuevas reglas de validación con el asistente](#a2-crear-nuevas-reglas-de-validación-con-el-asistente)
  - [A.3 Tipos de reglas disponibles](#a3-tipos-de-reglas-disponibles)
- [Documento B. Construcción del mensaje ideal](#documento-b-construcción-del-mensaje-ideal)
  - [B.1 Estructura base del mensaje](#b1-estructura-base-del-mensaje)
  - [B.2 Ejemplos de mensajes por tipo de dato](#b2-ejemplos-de-mensajes-por-tipo-de-dato)
  - [B.3 Palabras clave, ejemplos de respuesta y errores frecuentes](#b3-palabras-clave-ejemplos-de-respuesta-y-errores-frecuentes)
- [Documento C. Interpretación de las respuestas del asistente](#documento-c-interpretación-de-las-respuestas-del-asistente)
  - [C.1 Formato de respuesta estándar](#c1-formato-de-respuesta-estándar)
  - [C.2 Ajustes sugeridos según el tipo de regla](#c2-ajustes-sugeridos-según-el-tipo-de-regla)
- [Documento D. Buenas prácticas y recomendaciones](#documento-d-buenas-prácticas-y-recomendaciones)
  - [D.1 Uso en sesiones colaborativas](#d1-uso-en-sesiones-colaborativas)
  - [D.2 Checklist antes de publicar una regla](#d2-checklist-antes-de-publicar-una-regla)

---

## Documento A. Flujo general del asistente

Esta sección explica paso a paso cómo interactuar con el asistente inteligente para consultar, crear y gestionar reglas de validación. El objetivo es garantizar que cada solicitud cuente con el contexto necesario para producir respuestas completas y consistentes.

### A.1 Solicitar reglas de validación existentes

1. **Identificar el contexto.** Reúne la información básica de la plantilla o del campo de datos para el que deseas conocer las reglas vigentes (por ejemplo, nombre del dataset, columna específica y objetivo de negocio).
2. **Construir el mensaje.** Usa la estructura descrita en la sección [B.1](#b1-estructura-base-del-mensaje) e incluye palabras clave como "listar reglas", "detalles de validación" o "errores asociados".
3. **Enviar la solicitud.** Realiza una petición `POST /assistant/analyze` con el encabezado `Authorization` y el mensaje preparado.
4. **Validar la respuesta.** El asistente devolverá un objeto con los campos `Nombre de la regla`, `Tipo de dato`, `Mensaje de error`, `Descripción`, `Ejemplo`, `Header` y `Regla`.
5. **Registrar resultados.** Documenta la respuesta en el repositorio de reglas internas para mantener un historial versionado y reutilizable.

> **Ejemplo de mensaje para solicitar reglas existentes:**
> ```json
> {
>   "message": "Enumera todas las reglas activas para la columna 'Monto Factura' de la plantilla Ventas Retail 2024 y explica qué error muestran cuando fallan."
> }
> ```

### A.2 Crear nuevas reglas de validación con el asistente

1. **Definir el objetivo de la regla.** Determina qué quiere validar (por ejemplo, formatos, listas, dependencias, rangos) y cuál es el impacto de negocio.
2. **Preparar los parámetros clave.** Identifica encabezados, valores límite, catálogo permitido, dependencias y ejemplos válidos/ inválidos.
3. **Redactar el mensaje al asistente.** Solicita explícitamente la generación de una nueva regla, indicando el tipo de dato, condiciones obligatorias y mensaje de error deseado.
4. **Analizar la respuesta.** Revisa que el asistente entregue todos los campos necesarios (`Nombre de la regla`, `Tipo de dato`, etc.) y valida la coherencia del ejemplo con la descripción.
5. **Guardar y versionar.** Integra la regla a la plantilla correspondiente y guarda la conversación en el repositorio de documentación.

> **Ejemplo de mensaje para crear reglas:**
> ```json
> {
>   "message": "Crea una regla de validación para el campo 'Fecha de Pago' que impida fechas anteriores a 2020 y sugiera el mensaje de error adecuado. Incluye ejemplos válidos e inválidos." 
> }
> ```

### A.3 Tipos de reglas disponibles

Los tipos de reglas más utilizados se agrupan en las siguientes categorías. Incluye el tipo de dato y las condiciones que cada regla puede manejar.

| Tipo de regla | Descripción | Uso típico | Campos clave en `Header` |
| --- | --- | --- | --- |
| **Lista** | Valida que el valor esté dentro de una lista de opciones permitidas. | Catálogos de monedas, países o estados. | `Lista` con los valores aceptados. |
| **Rango numérico** | Confirma que el dato numérico se mantenga entre un mínimo y un máximo. | Validaciones de montos, porcentajes o cantidades. | `Valor mínimo`, `Valor máximo`, `Inclusivo` (opcional). |
| **Formato (expresión regular)** | Asegura un formato específico usando patrones regex. | Números de documento, códigos alfanuméricos, correos. | `Regex`, `Descripción del formato`. |
| **Dependencia** | Valida campos según la combinación de valores en otras columnas. | Relación Tipo de documento vs. Número, Estado vs. Fecha. | Lista de columnas dependientes y sus parámetros. |
| **Fecha** | Establece límites de fechas válidas o rangos dinámicos. | Periodos contables, fechas de corte y vigencias. | `Fecha mínima`, `Fecha máxima`, `Formato esperado`. |
| **Longitud** | Controla el número de caracteres permitidos. | Códigos internos, identificadores numéricos. | `Longitud mínima`, `Longitud máxima`. |
| **Booleano** | Confirma que solo se acepten valores `true/false` o equivalentes. | Bandera de estados, confirmaciones. | `Valores aceptados`, `Normalización` (opcional). |
| **Personalizada** | Implementa lógica compleja definida por el negocio. | Reglas de cálculo o validaciones multi-etapa. | `Descripción de lógica`, `Parámetros`. |

#### A.3.1 JSON de referencia para reglas de tipo Lista

```json
{
  "Nombre de la regla": "Lista de países autorizados",
  "Tipo de dato": "Lista",
  "Campo obligatorio": true,
  "Mensaje de error": "El país seleccionado no pertenece al catálogo vigente.",
  "Descripción": "La columna 'País de residencia' solo admite códigos ISO 3166 alfa-3 aprobados por el área de cumplimiento.",
  "Ejemplo": {
    "Válidos": ["MEX", "COL", "PER"],
    "Inválidos": ["MEXICO", "ZZZ", ""]
  },
  "Header": {
    "Columna": "PaisResidencia",
    "Catalogo": "ISO-3166-ALPHA3",
    "VersionCatalogo": "2024-02"
  },
  "Regla": {
    "Tipo": "lista",
    "ValoresPermitidos": ["MEX", "COL", "PER", "ARG", "CHL"],
    "Normalizacion": {
      "Mayusculas": true,
      "TrimEspacios": true
    }
  }
}
```

#### A.3.2 JSON de referencia para reglas de Rango numérico

```json
{
  "Nombre de la regla": "Porcentaje de descuento permitido",
  "Tipo de dato": "Rango numérico",
  "Campo obligatorio": true,
  "Mensaje de error": "El descuento debe estar entre 0% y 15%.",
  "Descripción": "El campo 'Descuento aplicado' acepta porcentajes desde cero hasta quince, incluyendo ambos extremos.",
  "Ejemplo": {
    "Válidos": [0, 10.5, 15],
    "Inválidos": [-1, 15.1, 30]
  },
  "Header": {
    "Columna": "DescuentoAplicado",
    "Unidad": "porcentaje",
    "Decimales": 2
  },
  "Regla": {
    "Tipo": "rango",
    "ValorMinimo": 0,
    "ValorMaximo": 15,
    "Inclusivo": {
      "Inferior": true,
      "Superior": true
    },
    "FormatoEntrada": "numero"
  }
}
```

#### A.3.3 JSON de referencia para reglas de Formato (expresión regular)

```json
{
  "Nombre de la regla": "Formato de número de pasaporte",
  "Tipo de dato": "Formato (expresión regular)",
  "Campo obligatorio": true,
  "Mensaje de error": "El número de pasaporte debe ser alfanumérico de 9 caracteres.",
  "Descripción": "El campo 'NumeroPasaporte' debe tener exactamente nueve caracteres alfanuméricos sin espacios ni símbolos adicionales.",
  "Ejemplo": {
    "Válidos": ["A12345678", "9BCDE4567"],
    "Inválidos": ["A1234", "ABCD-1234", "1234567890"]
  },
  "Header": {
    "Columna": "NumeroPasaporte",
    "FormatoEsperado": "AAA999999"
  },
  "Regla": {
    "Tipo": "regex",
    "Expresion": "^[A-Z0-9]{9}$",
    "Flags": "i",
    "DescripcionFormato": "Nueve caracteres alfanuméricos, sin espacios"
  }
}
```

#### A.3.4 JSON de referencia para reglas de Dependencia

```json
{
  "Nombre de la regla": "Longitud por tipo de documento",
  "Tipo de dato": "Dependencia",
  "Campo obligatorio": true,
  "Mensaje de error": "La longitud del documento no coincide con el tipo seleccionado.",
  "Descripción": "La columna 'NumeroDocumento' cambia su longitud esperada según el valor del campo 'TipoDocumento'.",
  "Ejemplo": {
    "Válidos": [
      { "TipoDocumento": "DNI", "NumeroDocumento": "12345678" },
      { "TipoDocumento": "PAS", "NumeroDocumento": "A1234567" }
    ],
    "Inválidos": [
      { "TipoDocumento": "DNI", "NumeroDocumento": "1234" },
      { "TipoDocumento": "PAS", "NumeroDocumento": "1234567890" }
    ]
  },
  "Header": {
    "Columnas": ["TipoDocumento", "NumeroDocumento"],
    "Dependencias": {
      "TipoDocumento": ["NumeroDocumento"]
    }
  },
  "Regla": {
    "Tipo": "dependencia",
    "Condiciones": [
      {
        "Cuando": { "TipoDocumento": "DNI" },
        "Validacion": {
          "Longitud": 8,
          "SoloDigitos": true
        }
      },
      {
        "Cuando": { "TipoDocumento": "PAS" },
        "Validacion": {
          "Longitud": 8,
          "Regex": "^[A-Z][0-9]{7}$"
        }
      }
    ],
    "MensajePersonalizado": true
  }
}
```

#### A.3.5 JSON de referencia para reglas de Fecha

```json
{
  "Nombre de la regla": "Fecha de emisión permitida",
  "Tipo de dato": "Fecha",
  "Campo obligatorio": true,
  "Mensaje de error": "La fecha de emisión no puede ser futura ni anterior al 2020-01-01.",
  "Descripción": "La columna 'FechaEmision' admite fechas desde el inicio de 2020 hasta el día actual, usando formato ISO 8601.",
  "Ejemplo": {
    "Válidos": ["2020-06-15", "2023-12-01"],
    "Inválidos": ["2019-12-31", "2025-01-01"]
  },
  "Header": {
    "Columna": "FechaEmision",
    "Formato": "YYYY-MM-DD",
    "ZonaHoraria": "America/Mexico_City"
  },
  "Regla": {
    "Tipo": "fecha",
    "FechaMinima": "2020-01-01",
    "FechaMaxima": "today",
    "IncluirMaxima": false,
    "ValidarZonaHoraria": true
  }
}
```

#### A.3.6 JSON de referencia para reglas de Longitud

```json
{
  "Nombre de la regla": "Longitud de identificador interno",
  "Tipo de dato": "Longitud",
  "Campo obligatorio": true,
  "Mensaje de error": "El identificador debe contener exactamente 12 caracteres.",
  "Descripción": "La columna 'IdInterno' debe tener doce caracteres alfanuméricos para mantener la compatibilidad con sistemas legados.",
  "Ejemplo": {
    "Válidos": ["A1B2C3D4E5F6"],
    "Inválidos": ["1234567", "ABCDEFGHIJKLM"]
  },
  "Header": {
    "Columna": "IdInterno",
    "Relleno": {
      "Tipo": "izquierda",
      "Caracter": "0"
    }
  },
  "Regla": {
    "Tipo": "longitud",
    "LongitudMinima": 12,
    "LongitudMaxima": 12,
    "Normalizar": {
      "Trim": true,
      "Mayusculas": true
    }
  }
}
```

#### A.3.7 JSON de referencia para reglas Booleanas

```json
{
  "Nombre de la regla": "Indicador de cliente activo",
  "Tipo de dato": "Booleano",
  "Campo obligatorio": true,
  "Mensaje de error": "Solo se permiten las opciones Sí/No o True/False.",
  "Descripción": "La columna 'ClienteActivo' se normaliza a valores booleanos a partir de distintas representaciones textuales.",
  "Ejemplo": {
    "Válidos": ["Sí", "No", "true", "false", 1, 0],
    "Inválidos": ["Tal vez", "1.0", "verdadero"]
  },
  "Header": {
    "Columna": "ClienteActivo",
    "Normalizacion": "boolean"
  },
  "Regla": {
    "Tipo": "booleano",
    "ValoresAceptados": ["si", "sí", "no", "true", "false", 1, 0],
    "Mapeo": {
      "si": true,
      "sí": true,
      "true": true,
      "1": true,
      "no": false,
      "false": false,
      "0": false
    }
  }
}
```

#### A.3.8 JSON de referencia para reglas Personalizadas

```json
{
  "Nombre de la regla": "Validación de margen y tipo de producto",
  "Tipo de dato": "Personalizada",
  "Campo obligatorio": true,
  "Mensaje de error": "El margen debe corresponder al tipo de producto según la tabla de negocio.",
  "Descripción": "Combina varias condiciones: valida que el margen declarado cumpla con mínimos por categoría y que los productos premium tengan código especial.",
  "Ejemplo": {
    "Válidos": [
      { "TipoProducto": "Standard", "Margen": 0.25, "Codigo": "STD-001" },
      { "TipoProducto": "Premium", "Margen": 0.4, "Codigo": "PRM-999" }
    ],
    "Inválidos": [
      { "TipoProducto": "Standard", "Margen": 0.1, "Codigo": "STD-001" },
      { "TipoProducto": "Premium", "Margen": 0.3, "Codigo": "PRE-100" }
    ]
  },
  "Header": {
    "Columnas": ["TipoProducto", "Margen", "Codigo"],
    "FuenteReglas": "tabla_margenes_producto",
    "Version": "2024-03"
  },
  "Regla": {
    "Tipo": "personalizada",
    "Pseudocodigo": [
      "if TipoProducto == 'Standard' then Margen >= 0.2",
      "if TipoProducto == 'Premium' then Margen >= 0.35 and Codigo inicia con 'PRM-'"
    ],
    "Parametros": {
      "MargenMinimo": {
        "Standard": 0.2,
        "Premium": 0.35
      },
      "PrefijoCodigoPremium": "PRM-"
    }
  }
}
```

---

## Documento B. Construcción del mensaje ideal

Este documento guía la redacción de mensajes para que el asistente ofrezca respuestas precisas y completas.

### B.1 Estructura base del mensaje

1. **Contexto de negocio:** Describe el proceso, plantilla o flujo donde se aplicará la regla.
2. **Campo o conjunto de campos:** Menciona explícitamente el nombre de las columnas involucradas.
3. **Objetivo de la consulta:** Indica si deseas consultar, crear, modificar o eliminar reglas.
4. **Restricciones específicas:** Enumera límites, dependencias, formatos o catálogos que deban cumplirse.
5. **Formato de respuesta esperado:** Señala si la respuesta debe incluir ejemplos, encabezados específicos o estructura JSON.
6. **Palabras clave de guía:** Integra términos que orienten al asistente y disparen las secciones requeridas (ver [B.3](#b3-palabras-clave-ejemplos-de-respuesta-y-errores-frecuentes)).

> **Plantilla de mensaje recomendada:**
> ```text
> Hola asistente, necesito [acción: consultar/crear/actualizar] reglas para [nombre de plantilla o flujo].
> El campo principal es [nombre del campo] y debe cumplir con [restricciones o dependencias].
> Incluye palabras clave como "estructura JSON completa", "ejemplos válidos e inválidos" y "posibles errores operativos" para asegurar una respuesta detallada.
> Por favor responde usando la estructura estándar de reglas de validación, incluye ejemplos válidos e inválidos, posibles errores de captura y menciona el mensaje de error que se mostrará al usuario final.
> ```

### B.2 Ejemplos de mensajes por tipo de dato

- **Lista (catálogo):**
  ```json
  {
    "message": "Genera la regla de validación para 'Código de País' usando la lista oficial de ISO 3166 y detalla el mensaje de error cuando se ingresa un código fuera de la lista."
  }
  ```
- **Rango numérico:**
  ```json
  {
    "message": "Necesito validar que el campo 'Descuento' esté entre 0 y 15 por ciento, especifica si los extremos son inclusivos y dame ejemplos de valores aceptados y rechazados." 
  }
  ```
- **Formato (regex):**
  ```json
  {
    "message": "Define una regla para el campo 'Número de Pasaporte' que acepte el patrón alfanumérico de 9 caracteres y describe los errores para formatos inválidos." 
  }
  ```
- **Dependencia:**
  ```json
  {
    "message": "Crea una regla dependiente entre 'Tipo de documento' y 'Número de documento' donde el número cambie de longitud según el tipo seleccionado. Indica cada longitud y un ejemplo por tipo." 
  }
  ```
- **Fecha:**
  ```json
  {
    "message": "Consulta las reglas actuales del campo 'Fecha de Emisión' y verifica que no permita fechas futuras. Añade el mensaje de error que se muestra al usuario." 
  }
  ```
- **Booleano:**
  ```json
  {
    "message": "Solicito la regla para el campo '¿Cliente Activo?' que solo acepte 'Sí/No' y devuelva una normalización a valores booleanos."
  }
  ```

### B.3 Palabras clave, ejemplos de respuesta y errores frecuentes

| Palabra clave en el mensaje | Lo que dispara en la respuesta del asistente | Extracto esperado en la respuesta | Errores comunes si se omite |
| --- | --- | --- | --- |
| `"estructura JSON completa"` | Entrega del bloque `Regla` con todos los campos y subcampos. | Código JSON con `Tipo`, `Parametros`, `Condiciones`, etc. | Respuestas resumidas sin `Regla` ni detalle de parámetros. |
| `"ejemplos válidos e inválidos"` | Inclusión del campo `Ejemplo` con listas separadas. | Arrays diferenciados `"Válidos"` y `"Inválidos"`. | Ejemplos solo válidos o ausencia de casos negativos. |
| `"posibles errores operativos"` | Explicaciones de fallos frecuentes y mensajes de error asociados. | Texto adicional como "Se genera el error X cuando..." | Falta de contexto sobre cómo interpretar los mensajes de error. |
| `"mensaje de error mostrado"` | Garantiza el campo `Mensaje de error` literal. | Cadena explícita para mostrar al usuario final. | Mensajes genéricos o no alineados con UX. |
| `"cabeceras utilizadas"` | Completa el campo `Header` con columnas o metadatos. | Objeto `Header` con `Columna`, `Catalogo`, `Dependencias`, etc. | Ausencia de mapeo a columnas reales o pérdida de trazabilidad. |
| `"validaciones relacionadas"` | Permite al asistente proponer reglas complementarias. | Sección adicional con sugerencias de reglas auxiliares. | No se identifica impacto cruzado entre campos. |

---

## Documento C. Interpretación de las respuestas del asistente

### C.1 Formato de respuesta estándar

Cada respuesta del asistente debe contener los siguientes bloques. Si falta alguno, solicita una respuesta ampliada.

| Campo | Descripción | Notas |
| --- | --- | --- |
| `Nombre de la regla` | Identificador human-readable de la validación. | Debe ser único por plantilla. |
| `Tipo de dato` | Categoría de la regla (lista, rango, dependencia, etc.). | Alineada con los tipos definidos en [A.3](#a3-tipos-de-reglas-disponibles). |
| `Campo obligatorio` | Indica si el campo debe contener un valor. | Útil para interfaces de captura. |
| `Mensaje de error` | Texto que ve el usuario cuando la validación falla. | Revisar ortografía y claridad. |
| `Descripción` | Explica el propósito y lógica de la regla. | Incluye contexto de negocio. |
| `Ejemplo` | Muestra casos válidos e inválidos. | Debe ser consistente con la regla. |
| `Header` | Encabezados o columnas que la regla usa como referencia. | Define columnas exportables. |
| `Regla` | Contenido estructurado que el motor de validaciones consume. | Debe estar en JSON o formato acordado. |

### C.2 Ajustes sugeridos según el tipo de regla

- **Lista:** Revisa que todos los valores estén actualizados y coincididos con sistemas maestros. Usa mayúsculas consistentes.
- **Rango numérico:** Verifica unidades (por ejemplo, porcentajes vs. valores absolutos) y si los extremos son inclusivos.
- **Formato:** Asegura que la expresión regular esté documentada y prueba al menos dos casos válidos y dos inválidos.
- **Dependencia:** Confirma que todas las combinaciones posibles estén cubiertas y que el mensaje de error mencione ambos campos.
- **Fecha:** Define zona horaria y formato (por ejemplo, `YYYY-MM-DD`). Añade notas sobre valores por defecto.
- **Booleano:** Indica claramente cómo se transforman entradas como `"sí"`, `"no"`, `1`, `0`.
- **Personalizada:** Documenta la lógica paso a paso y adjunta diagramas o pseudocódigo si aplica.

---

## Documento D. Buenas prácticas y recomendaciones

### D.1 Uso en sesiones colaborativas

- Coordina con analistas de datos y dueños de proceso antes de solicitar cambios al asistente.
- Comparte el mensaje enviado y la respuesta obtenida para aprobación conjunta.
- Versiona los mensajes en un repositorio (por ejemplo, en un directorio `/assistant/prompts/`) para auditar la evolución de las reglas.
- Si surgen discrepancias, reenvía la conversación al asistente pidiendo aclaraciones específicas.

### D.2 Checklist antes de publicar una regla

1. **Contexto validado:** ¿El propósito de la regla está alineado con el proceso?
2. **Campos completos:** ¿La respuesta incluye todos los campos estándar (`Nombre`, `Tipo`, `Mensaje`, `Ejemplo`, etc.)?
3. **Pruebas rápidas:** ¿Se probaron al menos un caso válido y uno inválido con datos reales?
4. **Mensajes claros:** ¿El mensaje de error es comprensible para usuarios finales?
5. **Documentación actualizada:** ¿Se agregó la regla al catálogo central y a la plantilla correspondiente?
6. **Aprobación:** ¿El equipo de negocio autorizó la nueva o modificada regla?

Cumplir con este checklist asegura que las reglas generadas por el asistente sean confiables, auditables y fáciles de mantener.
