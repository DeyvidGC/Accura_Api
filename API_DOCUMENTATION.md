# Guía práctica y detallada de la API

Esta guía explica, paso a paso, cómo interactuar con cada servicio expuesto por la API. Está escrita en un lenguaje sencillo para que cualquier persona —incluso sin experiencia técnica— pueda entender qué hace cada endpoint, qué datos necesita y qué respuestas devuelve. Todos los ejemplos usan JSON (o se indica explícitamente cuando no es así).

## Convenciones generales

- **Autenticación:** salvo que se indique lo contrario, todos los endpoints requieren el encabezado `Authorization: Bearer <token>` obtenido desde `/auth/token`.
- **Fechas:** se emplea el formato `AAAA-MM-DD` (por ejemplo `2024-05-28`).
- **Tiempos:** se muestran en ISO 8601 (`2024-05-28T12:30:00Z`).
- **Paginación:** cuando existan parámetros `skip` y `limit`, el comportamiento por defecto es `skip=0` y `limit=100`.
- **Roles:** el sistema distingue entre usuarios administradores y usuarios con acceso restringido. En cada endpoint se indica quién puede invocarlo.
- **Respuestas de error:** todos los ejemplos utilizan el formato estándar de FastAPI `{"detail": "mensaje"}` salvo que se indique lo contrario.

---

## Documento A. Autenticación

### A.1 Obtener un token de acceso
- **Método y URL:** `POST /auth/token`
- **Roles permitidos:** cualquier usuario con credenciales activas.
- **Encabezados obligatorios:** `Content-Type: application/x-www-form-urlencoded`
- **Datos posibles (form-data):**
```json
{
  "username": "usuario@correo.com",
  "password": "MiClave123"
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `username` | Cadena | Sí | Debe ser un correo electrónico registrado |
  | `password` | Cadena | Sí | Debe coincidir con la contraseña almacenada |
- **Respuesta 200 (éxito):**
```json
{
  "access_token": "jwt.token.generado",
  "token_type": "bearer",
  "role": "admin",
  "must_change_password": false
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "Credenciales incorrectas."}
    ```
  - `403 Forbidden`
    ```json
    {"detail": "El usuario está inactivo."}
    ```

### A.2 Generar el hash de una contraseña
- **Método y URL:** `POST /auth/hash-password`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "password": "NuevaContraseña123"
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `password` | Cadena | Sí | No debe estar vacía |
- **Respuesta 200 (éxito):**
```json
{
  "hashed_password": "cadena-cifrada"
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `403 Forbidden`
    ```json
    {"detail": "No tienes permisos para generar hashes."}
    ```

### A.3 Solicitar restablecimiento de contraseña
- **Método y URL:** `POST /auth/forgot-password`
- **Roles permitidos:** público.
- **Encabezados obligatorios:** `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "email": "usuario@gmail.com"
}
```
- **Descripción:** envía una contraseña temporal al correo si está registrado. La respuesta es intencionalmente genérica para proteger la confidencialidad de los usuarios.
- **Respuesta 202 (éxito):**
```json
{
  "message": "Si el correo está registrado, recibirás un mensaje con una contraseña temporal."
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "El correo electrónico debe ser una cuenta de Gmail válida"}
    ```

---

## Documento B. Gestión de usuarios

Los usuarios poseen un **nombre** (máximo 50 caracteres), un **correo electrónico** de Gmail único y un **rol** asociado (`role_id` ≥ 1).

### B.1 Crear un usuario
- **Método y URL:** `POST /users/`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "name": "Ana López",
  "email": "ana.lopez@gmail.com",
  "role_id": 2
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `name` | Cadena | Sí | Máximo 50 caracteres |
  | `email` | Email | Sí | Debe ser una cuenta de Gmail válida y única |
  | `role_id` | Entero | Sí | Valor mínimo 1 |
- **Respuesta 201 (éxito):**
```json
{
  "id": 12,
  "name": "Ana López",
  "email": "ana.lopez@gmail.com",
  "role_id": 2,
  "is_active": true,
  "temporary_password": "XZ29kd$!"
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "El correo ya está registrado."}
    ```
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### B.2 Consultar mi perfil
- **Método y URL:** `GET /users/me`
- **Roles permitidos:** cualquier usuario autenticado.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de consulta:** ninguno.
- **Respuesta 200 (éxito):**
```json
{
  "id": 8,
  "name": "Ana López",
  "email": "ana.lopez@gmail.com",
  "role_id": 2,
  "is_active": true,
  "must_change_password": false
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "Token expirado o inválido."}
    ```

### B.3 Listar usuarios
- **Método y URL:** `GET /users/`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de consulta opcionales:**
  | Parámetro | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `skip` | Entero | No | ≥ 0 |
  | `limit` | Entero | No | ≥ 1, por defecto 100 |
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 8,
      "name": "Ana López",
      "email": "ana.lopez@gmail.com",
      "role_id": 2,
      "is_active": true
    },
    {
      "id": 9,
      "name": "Carlos Pérez",
      "email": "carlos.perez@gmail.com",
      "role_id": 3,
      "is_active": false
    }
  ],
  "total": 2
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### B.4 Ver un usuario específico
- **Método y URL:** `GET /users/{user_id}`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de ruta:** `user_id` (entero ≥ 1).
- **Respuesta 200 (éxito):**
```json
{
  "id": 9,
  "name": "Carlos Pérez",
  "email": "carlos.perez@gmail.com",
  "role_id": 3,
  "is_active": false
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Usuario no encontrado."}
    ```

### B.5 Actualizar un usuario
- **Método y URL:** `PUT /users/{user_id}`
- **Roles permitidos:** administradores (todos los campos) o el propio usuario (solo nombre + contraseña con validación adicional).
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "name": "Ana Renovada",
  "email": "ana.lopez@gmail.com",
  "password": "ClaveSegura123",
  "is_active": true,
  "role_id": 2
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `name` | Cadena | No | Máximo 50 caracteres |
  | `email` | Email | No | Solo modificable por administradores |
  | `password` | Cadena | No | Mínimo 8 caracteres; obligatorio para que un usuario no administrador actualice sus datos |
  | `is_active` | Booleano | No | Solo modificable por administradores |
  | `role_id` | Entero | No | Solo modificable por administradores, valor mínimo 1 |
- **Regla de validación destacada:**
```json
{
  "Nombre de la regla": "Actualización segura de perfil",
  "Tipo de dato": "Dependencia",
  "Campo obligatorio": false,
  "Mensaje de error": "El usuario debe proporcionar su contraseña actual para modificar sus datos personales.",
  "Descripción": "Controla que los usuarios sin privilegios administrativos confirmen su identidad antes de realizar cambios.",
  "Ejemplo": {
    "válido": {
      "password": "MiClaveSegura",
      "name": "Ana Renovada"
    },
    "inválido": {
      "name": "Cambio sin contraseña"
    }
  },
  "Header": [
    "password",
    "Longitud minima",
    "Longitud maxima"
  ],
  "Regla": {
    "reglas especifica": [
      {
        "password": true,
        "Texto": {
          "Longitud minima": 8,
          "Longitud maxima": 128
        }
      }
    ]
  }
}
```
- **Respuesta 200 (éxito):**
```json
{
  "id": 8,
  "name": "Ana Renovada",
  "email": "ana.lopez@gmail.com",
  "role_id": 2,
  "is_active": true
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "La contraseña no puede estar vacía cuando se envía."}
    ```
  - `403 Forbidden`
    ```json
    {"detail": "Intento de modificar campos restringidos."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Usuario no encontrado."}
    ```

### B.6 Restablecer la contraseña de un usuario
- **Método y URL:** `POST /users/{user_id}/reset-password`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de ruta:** `user_id` (entero ≥ 1).
- **Datos posibles:** no requiere cuerpo.
- **Respuesta 200 (éxito):**
```json
{
  "id": 9,
  "temporary_password": "Abc123$%",
  "must_change_password": true
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Usuario no encontrado."}
    ```

### B.7 Eliminar un usuario
- **Método y URL:** `DELETE /users/{user_id}`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de ruta:** `user_id` (entero ≥ 1).
- **Respuesta 204 (éxito):** sin cuerpo.
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Usuario no encontrado."}
    ```

---

## Documento C. Plantillas (Templates)

Las plantillas definen la estructura de los datos que se cargarán y las reglas asociadas a cada columna.

### C.1 Crear una plantilla
- **Método y URL:** `POST /templates/`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "name": "Ventas Retail 2024",
  "description": "Plantilla para seguimiento de ventas.",
  "status": "unpublished",
  "table_name": "ventas_retail_2024",
  "is_active": true
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `name` | Cadena | Sí | Máximo 50 caracteres |
  | `table_name` | Cadena | Sí | Máximo 63 caracteres, debe ser único |
  | `description` | Cadena | No | Máximo 255 caracteres |
  | `status` | Enumeración | No | Valores permitidos: `unpublished`, `published` |
  | `is_active` | Booleano | No | Valor por defecto `true` |
- **Respuesta 201 (éxito):**
```json
{
  "id": 3,
  "name": "Ventas Retail 2024",
  "description": "Plantilla para seguimiento de ventas.",
  "status": "unpublished",
  "table_name": "ventas_retail_2024",
  "is_active": true,
  "created_at": "2024-05-28T12:30:00Z"
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "El nombre de la tabla ya existe."}
    ```
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### C.2 Listar plantillas
- **Método y URL:** `GET /templates/`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de consulta opcionales:** `skip` (entero ≥ 0), `limit` (entero ≥ 1).
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 3,
      "name": "Ventas Retail 2024",
      "status": "unpublished",
      "is_active": true
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### C.3 Ver una plantilla específica
- **Método y URL:** `GET /templates/{template_id}`
- **Roles permitidos:** administradores o usuarios con acceso concedido.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de ruta:** `template_id` (entero ≥ 1).
- **Respuesta 200 (éxito):**
```json
{
  "id": 3,
  "name": "Ventas Retail 2024",
  "description": "Plantilla para seguimiento de ventas.",
  "status": "unpublished",
  "table_name": "ventas_retail_2024",
  "is_active": true,
  "columns": [
    {
      "id": 15,
      "name": "monto",
      "data_type": "decimal",
      "rule_ids": [6]
    }
  ]
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `403 Forbidden`
    ```json
    {"detail": "No tienes acceso a esta plantilla."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

### C.4 Actualizar una plantilla
- **Método y URL:** `PUT /templates/{template_id}`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "name": "Ventas Retail 2024",
  "description": "Actualización de alcance",
  "status": "published",
  "table_name": "ventas_retail_2024",
  "is_active": true
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `name` | Cadena | No | Máximo 50 caracteres |
  | `description` | Cadena | No | Máximo 255 caracteres |
  | `status` | Enumeración | No | Valores permitidos reales: `unpublished`, `published` |
  | `table_name` | Cadena | No | Máximo 63 caracteres |
  | `is_active` | Booleano | No | — |
- **Respuesta 200 (éxito):**
```json
{
  "id": 3,
  "name": "Ventas Retail 2024",
  "description": "Actualización de alcance",
  "status": "published",
  "table_name": "ventas_retail_2024",
  "is_active": true
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Valores inválidos para el estado."}
    ```
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

### C.5 Cambiar solo el estado de una plantilla
- **Método y URL:** `PATCH /templates/{template_id}/status`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "status": "published"
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `status` | Enumeración | Sí | `published` o `unpublished` |
- **Respuesta 200 (éxito):**
```json
{
  "id": 3,
  "status": "published",
  "updated_at": "2024-05-29T09:00:00Z"
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Estado inválido."}
    ```
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

### C.6 Eliminar una plantilla
- **Método y URL:** `DELETE /templates/{template_id}`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`
- **Parámetros de ruta:** `template_id` (entero ≥ 1).
- **Respuesta 204 (éxito):** sin cuerpo.
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

### C.7 Gestionar columnas de una plantilla

#### C.7.1 Crear una o varias columnas
- **Método y URL:** `POST /templates/{template_id}/columns`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles (única columna):**
```json
{
  "name": "monto",
  "data_type": "decimal",
  "description": "Monto de la transacción",
  "rule_ids": [6]
}
```
- **Datos posibles (varias columnas):**
```json
{
  "columns": [
    {
      "name": "monto",
      "data_type": "decimal",
      "rule_ids": [6]
    },
    {
      "name": "moneda",
      "data_type": "string",
      "rule_ids": [7]
    }
  ]
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `name` | Cadena | Sí | Máximo 50 caracteres |
  | `data_type` | Cadena | Sí | Máximo 50 caracteres |
  | `description` | Cadena | No | Máximo 255 caracteres |
  | `rule_ids` | Lista de enteros | No | Debe referenciar reglas existentes (≥ 1) |
- **Respuesta 201 (éxito):**
```json
{
  "columns": [
    {
      "id": 15,
      "name": "monto",
      "data_type": "decimal",
      "rule_ids": [6]
    }
  ]
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Formato de columnas inválido."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

#### C.7.2 Listar columnas
- **Método y URL:** `GET /templates/{template_id}/columns`
- **Roles permitidos:** administradores o usuarios con acceso a la plantilla.
- **Encabezados obligatorios:** `Authorization`
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 15,
      "name": "monto",
      "data_type": "decimal",
      "rule_ids": [6],
      "is_active": true
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

#### C.7.3 Ver una columna específica
- **Método y URL:** `GET /templates/{template_id}/columns/{column_id}`
- **Roles permitidos:** administradores o usuarios con acceso a la plantilla.
- **Respuesta 200 (éxito):**
```json
{
  "id": 15,
  "name": "monto",
  "data_type": "decimal",
  "description": "Monto de la transacción",
  "rule_ids": [6],
  "is_active": true
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Columna no encontrada."}
    ```

#### C.7.4 Actualizar una columna
- **Método y URL:** `PUT /templates/{template_id}/columns/{column_id}`
- **Roles permitidos:** administradores.
- **Datos posibles:**
```json
{
  "name": "monto",
  "data_type": "decimal",
  "description": "Actualización de descripción",
  "rule_ids": [6],
  "is_active": true
}
```
- **Respuesta 200 (éxito):**
```json
{
  "id": 15,
  "name": "monto",
  "data_type": "decimal",
  "description": "Actualización de descripción",
  "rule_ids": [6],
  "is_active": true
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Datos de columna inválidos."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Columna no encontrada."}
    ```

#### C.7.5 Eliminar una columna
- **Método y URL:** `DELETE /templates/{template_id}/columns/{column_id}`
- **Roles permitidos:** administradores.
- **Respuesta 204 (éxito):** sin cuerpo.
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Columna no encontrada."}
    ```

### C.8 Administrar accesos a una plantilla

#### C.8.1 Conceder acceso
- **Método y URL:** `POST /templates/{template_id}/access`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "user_id": 8,
  "start_date": "2024-05-01",
  "end_date": "2024-12-31"
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `user_id` | Entero | Sí | Debe existir en la base de datos, ≥ 1 |
  | `start_date` | Fecha | No | Fecha inicial de vigencia |
  | `end_date` | Fecha | No | Debe ser posterior o igual a `start_date` |
- **Respuesta 201 (éxito):**
```json
{
  "id": 21,
  "user_id": 8,
  "template_id": 3,
  "start_date": "2024-05-01",
  "end_date": "2024-12-31",
  "is_active": true
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "La fecha de fin debe ser mayor o igual a la fecha de inicio."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla o usuario no encontrado."}
    ```

#### C.8.2 Listar accesos
- **Método y URL:** `GET /templates/{template_id}/access`
- **Roles permitidos:** administradores.
- **Parámetros de consulta opcionales:** `include_inactive` (booleano).
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 21,
      "user_id": 8,
      "start_date": "2024-05-01",
      "end_date": "2024-12-31",
      "is_active": true
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

#### C.8.3 Revocar acceso
- **Método y URL:** `POST /templates/access/revoke`
- **Roles permitidos:** administradores.
- **Cuerpo (JSON):**
```json
[
  {
    "template_id": 3,
    "user_id": 8
  }
]
```
- **Respuesta 200 (éxito):**
```json
{
  "id": 21,
  "user_id": 8,
  "template_id": 3,
  "revoked_at": "2024-06-01T10:00:00Z",
  "is_active": false
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Acceso no encontrado."}
    ```

#### C.8.4 Listar plantillas publicadas por usuario
- **Método y URL:** `GET /templates/users/{user_id}`
- **Roles permitidos:** administradores o el propio usuario.
- **Respuesta 200 (éxito):**
```json
[
  {
    "id": 3,
    "user_id": 5,
    "name": "Ventas Retail",
    "status": "published",
    "description": "Plantilla de cargas de ventas.",
    "table_name": "ventas_retail_2024",
    "created_at": "2024-01-10T10:00:00Z",
    "updated_at": "2024-04-02T18:30:00Z",
    "is_active": true,
    "deleted": false,
    "deleted_by": null,
    "deleted_at": null,
    "columns": []
  }
]
```
- **Errores frecuentes:**
  - `403 Forbidden`
    ```json
    {"detail": "No autorizado"}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Usuario no encontrado"}
    ```

### C.9 Descargar el archivo base en Excel
- **Método y URL:** `GET /templates/{template_id}/excel`
- **Roles permitidos:** usuarios con acceso vigente a la plantilla.
- **Respuesta 200 (éxito):** archivo `.xlsx` binario.
- **Errores frecuentes:**
  - `403 Forbidden`
    ```json
    {"detail": "No tienes acceso a esta plantilla."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

---

## Documento D. Cargas de datos

### D.1 Subir un archivo para validar
- **Método y URL:** `POST /templates/{template_id}/loads`
- **Roles permitidos:** usuarios con acceso a la plantilla.
- **Encabezados obligatorios:** `Authorization`
- **Formato:** `multipart/form-data` con un campo `file`.
- **Validación destacada:**
```json
{
  "Nombre de la regla": "Validación de archivo de carga",
  "Tipo de dato": "Documento",
  "Campo obligatorio": true,
  "Mensaje de error": "Debes adjuntar un archivo Excel (.xlsx) para iniciar la validación.",
  "Descripción": "Solo se aceptan archivos en formato XLSX. El tamaño máximo depende de la configuración del servidor.",
  "Ejemplo": {
    "válido": "ventas_mayo.xlsx",
    "inválido": "ventas.txt"
  },
  "Regla": {
    "Longitud minima": 5,
    "Longitud maxima": 255
  }
}
```
- **Respuesta 201 (éxito):**
```json
{
  "message": "Archivo cargado correctamente",
  "load": {
    "id": 12,
    "template_id": 3,
    "user_id": 8,
    "status": "pending",
    "file_name": "ventas_mayo.xlsx",
    "total_rows": 0,
    "error_rows": 0,
    "report_path": null,
    "created_at": "2024-05-28T12:30:00Z",
    "started_at": null,
    "finished_at": null
  }
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Debes adjuntar un archivo .xlsx."}
    ```
  - `403 Forbidden`
    ```json
    {"detail": "No tienes acceso a esta plantilla."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Plantilla no encontrada."}
    ```

### D.2 Listar mis cargas
- **Método y URL:** `GET /loads`
- **Roles permitidos:** usuarios autenticados.
- **Parámetros de consulta opcionales:** `template_id` (entero ≥ 1), `skip` (≥ 0), `limit` (≥ 1).
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 12,
      "template_id": 3,
      "status": "pending",
      "file_name": "ventas_mayo.xlsx",
      "created_at": "2024-05-28T12:30:00Z"
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### D.3 Ver detalles de una carga
- **Método y URL:** `GET /loads/{load_id}`
- **Roles permitidos:** usuarios con acceso a la plantilla de la carga.
- **Respuesta 200 (éxito):**
```json
{
  "id": 12,
  "template_id": 3,
  "user_id": 8,
  "status": "processing",
  "file_name": "ventas_mayo.xlsx",
  "total_rows": 1000,
  "error_rows": 15,
  "report_path": "reports/loads/12.xlsx",
  "created_at": "2024-05-28T12:30:00Z",
  "started_at": "2024-05-28T12:31:00Z",
  "finished_at": null
}
```
- **Errores frecuentes:**
  - `403 Forbidden`
    ```json
    {"detail": "No tienes acceso a los detalles de esta carga."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Carga no encontrada."}
    ```

### D.4 Descargar el reporte de validación
- **Método y URL:** `GET /loads/{load_id}/report`
- **Roles permitidos:** usuarios con acceso a la plantilla.
- **Respuesta 200 (éxito):** archivo `.xlsx` con el reporte.
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Reporte aún no disponible."}
    ```

---

## Documento E. Archivos digitales

### E.1 Listar archivos digitales
- **Método y URL:** `GET /digital-files/`
- **Roles permitidos:** administradores.
- **Parámetros de consulta opcionales:** `template_id` (entero ≥ 1), `skip` (≥ 0), `limit` (≥ 1).
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 5,
      "template_id": 3,
      "file_name": "ventas_retail_2024.zip",
      "uploaded_at": "2024-05-28T12:30:00Z"
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### E.2 Ver un archivo digital específico
- **Método y URL:** `GET /digital-files/{digital_file_id}`
- **Roles permitidos:** administradores.
- **Respuesta 200 (éxito):**
```json
{
  "id": 5,
  "template_id": 3,
  "file_name": "ventas_retail_2024.zip",
  "uploaded_at": "2024-05-28T12:30:00Z",
  "size": 1048576
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Archivo digital no encontrado."}
    ```

### E.3 Obtener un archivo por plantilla
- **Método y URL:** `GET /digital-files/by-template/{template_id}`
- **Roles permitidos:** administradores.
- **Respuesta 200 (éxito):** archivo binario.
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "No existe archivo para esta plantilla."}
    ```

---

## Documento F. Registro de auditoría

### F.1 Listar entradas de auditoría
- **Método y URL:** `GET /audit-logs/`
- **Roles permitidos:** administradores.
- **Parámetros de consulta opcionales:** `template_name` (cadena), `skip`, `limit`.
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 31,
      "template_name": "Ventas Retail 2024",
      "action": "create",
      "performed_by": "admin@gmail.com",
      "performed_at": "2024-05-28T12:30:00Z"
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### F.2 Ver una entrada específica
- **Método y URL:** `GET /audit-logs/{entry_id}`
- **Roles permitidos:** administradores.
- **Respuesta 200 (éxito):**
```json
{
  "id": 31,
  "template_name": "Ventas Retail 2024",
  "action": "create",
  "payload": {
    "name": "Ventas Retail 2024",
    "table_name": "ventas_retail_2024"
  },
  "performed_by": "admin@gmail.com",
  "performed_at": "2024-05-28T12:30:00Z"
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Registro de auditoría no encontrado."}
    ```

---

## Documento G. Reglas de validación

Las reglas permiten definir validaciones avanzadas para las columnas de las plantillas. El campo `rule` acepta estructuras JSON complejas.

### G.1 Crear una regla
- **Método y URL:** `POST /rules/`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "rule": {
    "Nombre de la regla": "Validación de moneda",
    "Tipo de dato": "Lista",
    "Campo obligatorio": true,
    "Mensaje de error": "El valor de moneda debe ser uno de los siguientes: MXN, USD, EUR.",
    "Descripción": "Este campo valida que la moneda seleccionada sea una de las opciones permitidas en el sector asegurador: MXN, USD o EUR. La moneda es obligatoria y por defecto es MXN.",
    "Ejemplo": {
      "válido": "USD",
      "inválido": "GBP"
    },
    "Header": [
      "Lista"
    ],
    "Regla": {
      "Lista": [
        "MXN",
        "USD",
        "EUR"
      ]
    }
  },
  "is_active": true
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `rule` | Objeto o Lista | Sí | Debe contener la definición estructurada |
  | `is_active` | Booleano | No | Valor por defecto `true` |
- **Respuesta 201 (éxito):**
```json
{
  "id": 6,
  "rule": {
    "Nombre de la regla": "Validación de moneda",
    "Tipo de dato": "Lista",
    "Campo obligatorio": true,
    "Mensaje de error": "El valor de moneda debe ser uno de los siguientes: MXN, USD, EUR.",
    "Descripción": "Este campo valida que la moneda seleccionada sea una de las opciones permitidas en el sector asegurador: MXN, USD o EUR. La moneda es obligatoria y por defecto es MXN.",
    "Ejemplo": {
      "válido": "USD",
      "inválido": "GBP"
    },
    "Header": [
      "Lista"
    ],
    "Regla": {
      "Lista": [
        "MXN",
        "USD",
        "EUR"
      ]
    }
  },
  "is_active": true
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "El campo rule es obligatorio."}
    ```

### G.2 Listar reglas
- **Método y URL:** `GET /rules/`
- **Roles permitidos:** administradores.
- **Parámetros de consulta opcionales:** `skip`, `limit`.
- **Respuesta 200 (éxito):**
```json
{
  "items": [
    {
      "id": 6,
      "is_active": true,
      "created_at": "2024-05-28T12:30:00Z"
    }
  ],
  "total": 1
}
```
- **Errores frecuentes:**
  - `401 Unauthorized`
    ```json
    {"detail": "No autenticado."}
    ```

### G.3 Ver una regla
- **Método y URL:** `GET /rules/{rule_id}`
- **Roles permitidos:** administradores.
- **Respuesta 200 (éxito):**
```json
{
  "id": 6,
  "rule": {
    "Nombre de la regla": "Validación de moneda",
    "Tipo de dato": "Lista",
    "Campo obligatorio": true,
    "Mensaje de error": "El valor de moneda debe ser uno de los siguientes: MXN, USD, EUR.",
    "Descripción": "Este campo valida que la moneda seleccionada sea una de las opciones permitidas.",
    "Ejemplo": {
      "válido": "MXN",
      "inválido": "GBP"
    },
    "Header": [
      "Lista"
    ],
    "Regla": {
      "Lista": [
        "MXN",
        "USD",
        "EUR"
      ]
    }
  },
  "is_active": true
}
```
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Regla no encontrada."}
    ```

### G.4 Actualizar una regla
- **Método y URL:** `PUT /rules/{rule_id}`
- **Roles permitidos:** administradores.
- **Datos posibles:**
```json
{
  "rule": {
    "Nombre de la regla": "Validación de moneda",
    "Tipo de dato": "Lista",
    "Campo obligatorio": true,
    "Mensaje de error": "El valor de moneda debe ser uno de los siguientes: MXN, USD, EUR.",
    "Descripción": "Actualización del catálogo de monedas permitidas.",
    "Ejemplo": {
      "válido": "EUR",
      "inválido": "GBP"
    },
    "Header": [
      "Lista"
    ],
    "Regla": {
      "Lista": [
        "MXN",
        "USD",
        "EUR"
      ]
    }
  },
  "is_active": false
}
```
- **Respuesta 200 (éxito):**
```json
{
  "id": 6,
  "is_active": false,
  "updated_at": "2024-05-29T09:00:00Z"
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "Formato de rule inválido."}
    ```
  - `404 Not Found`
    ```json
    {"detail": "Regla no encontrada."}
    ```

### G.5 Eliminar una regla
- **Método y URL:** `DELETE /rules/{rule_id}`
- **Roles permitidos:** administradores.
- **Respuesta 204 (éxito):** sin cuerpo.
- **Errores frecuentes:**
  - `404 Not Found`
    ```json
    {"detail": "Regla no encontrada."}
    ```

### G.6 Regla de dependencia por tipo de documento
- **Descripción:** ejemplo de una validación dependiente donde el formato del número de documento varía según el tipo seleccionado.
- **Nota:** El arreglo `Header` de las reglas de dependencia debe incluir el campo dependiente y los encabezados propios de cada tipo configurado (por ejemplo, `Longitud minima` y `Longitud maxima` para reglas de documentos).
- **Estructura:**
```json
{
  "Nombre de la regla": "Número de documento según tipo de documento",
  "Tipo de dato": "Dependencia",
  "Campo obligatorio": true,
  "Mensaje de error": "El número de documento no cumple con la longitud requerida para el tipo de documento seleccionado.",
  "Descripción": "Valida que el número de documento tenga la longitud correcta dependiendo del tipo de documento seleccionado en la lista (DNI, Pasaporte, RUC, etc.) para documentos peruanos.",
  "Ejemplo": {
    "Válido": {
      "Tipo de documento": "DNI",
      "Número de documento": "12345678"
    },
    "Inválido": {
      "Tipo de documento": "RUC",
      "Número de documento": "12345678"
    }
  },
  "Header": [
    "Tipo Documento",
    "Longitud minima",
    "Longitud maxima"
  ],
  "Regla": {
    "reglas especifica": [
      {
        "Tipo Documento": "DNI",
        "Documento": {
          "Longitud minima": 8,
          "Longitud maxima": 8
        }
      },
      {
        "Tipo Documento": "RUC",
        "Documento": {
          "Longitud minima": 9,
          "Longitud maxima": 12
        }
      },
      {
        "Tipo Documento": "PASAPORTE",
        "Documento": {
          "Longitud minima": 11,
          "Longitud maxima": 11
        }
      }
    ]
  }
}
```

---

## Documento H. Asistente inteligente

### H.1 Solicitar análisis del asistente
- **Método y URL:** `POST /assistant/analyze`
- **Roles permitidos:** administradores.
- **Encabezados obligatorios:** `Authorization`, `Content-Type: application/json`
- **Datos posibles:**
```json
{
  "message": "Analiza las reglas activas y dime si la validación de moneda permite MXN y cuál es el error que devuelve cuando falla."
}
```
- **Campos y validaciones:**
  | Campo | Tipo | Obligatorio | Validaciones |
  | --- | --- | --- | --- |
  | `message` | Cadena | Sí | Longitud mínima de 1 carácter |
- **Respuesta 200 (éxito):**
```json
{
  "Nombre de la regla": "Validación de moneda",
  "Tipo de dato": "Lista",
  "Campo obligatorio": true,
  "Mensaje de error": "El valor de moneda debe ser uno de los siguientes: MXN, USD, EUR.",
  "Descripción": "La regla confirma que la moneda pertenece al catálogo permitido para reportes financieros.",
  "Ejemplo": {
    "válido": "MXN",
    "inválido": "GBP"
  },
  "Header": [
    "Lista"
  ],
  "Regla": {
    "Lista": [
      "MXN",
      "USD",
      "EUR"
    ]
  }
}
```
- **Errores frecuentes:**
  - `400 Bad Request`
    ```json
    {"detail": "El mensaje no puede estar vacío."}
    ```
  - `502 Bad Gateway`
    ```json
    {"detail": "Error al comunicarse con el servicio de IA."}
    ```

---

## Documento I. Actividad reciente

### I.1 Consultar actividad reciente
- **Método y URL:** `GET /activity/recent`
- **Roles permitidos:** solo administradores.
- **Parámetros de consulta opcionales:** `limit` (entero, mínimo 1, máximo 100, por defecto 20) para indicar cuántos eventos recuperar.
- **Respuesta 200 (éxito):**
```json
[
  {
    "event_id": "load-42",
    "event_type": "load.uploaded",
    "summary": "María García cargó 'ventas_mayo.xlsx' en la plantilla 'Ventas Mensuales'.",
    "created_at": "2024-05-28T12:30:00Z",
    "metadata": {
      "load_id": 42,
      "template_id": 3,
      "template_name": "Ventas Mensuales",
      "user_id": 8,
      "user_name": "María García",
      "file_name": "ventas_mayo.xlsx"
    }
  },
  {
    "event_id": "access-15",
    "event_type": "template.access.granted",
    "summary": "Juan Pérez recibió acceso a la plantilla 'Inventario'.",
    "created_at": "2024-05-20T09:00:00Z",
    "metadata": {
      "access_id": 15,
      "template_id": 5,
      "template_name": "Inventario",
      "user_id": 11,
      "user_name": "Juan Pérez"
    }
  },
  {
    "event_id": "user-27",
    "event_type": "user.created",
    "summary": "Se creó el usuario 'Laura Méndez' con el rol 'Analista'.",
    "created_at": "2024-05-18T14:45:00Z",
    "metadata": {
      "user_id": 27,
      "name": "Laura Méndez",
      "email": "laura.mendez@example.com",
      "role_name": "Analista",
      "role_alias": "analyst"
    }
  }
]
```
- **Errores frecuentes:**
  - `403 Forbidden`
    ```json
    {"detail": "No autorizado"}
    ```

---

## Consejos finales

- Incluye siempre el encabezado `Authorization: Bearer <token>` en los endpoints que lo requieren.
- Repite el proceso de inicio de sesión cuando el token expire.
- Verifica los códigos de estado (`200`, `201`, `204`, `400`, `401`, `403`, `404`, `502`) para entender si la operación fue exitosa o si faltó información.
- Mantén un registro de las reglas de validación aplicadas a cada plantilla para que el asistente pueda generar respuestas contextualizadas.
