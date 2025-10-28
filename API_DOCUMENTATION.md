# Guía práctica de la API

Esta guía explica, paso a paso, cómo interactuar con cada servicio de la API. Está escrita en un lenguaje sencillo para que cualquier persona —incluso sin experiencia técnica— pueda entender qué hace cada endpoint, qué datos necesita y qué respuestas puede devolver.

> **Formato general de las solicitudes**
> - La mayoría de los endpoints reciben y devuelven información en formato JSON (texto con llaves `{ }`).
> - Cuando se solicitan archivos (por ejemplo, reportes en Excel) la respuesta será un documento para descargar.
> - Las fechas siguen el estándar `AAAA-MM-DD` (por ejemplo `2024-05-28`).

## 1. Autenticación
Antes de usar la API debes iniciar sesión para obtener un token de seguridad. Ese token se enviará en todas las solicitudes posteriores.

### 1.1 Obtener un token de acceso
- **Método y URL:** `POST /auth/token`
- **¿Para qué sirve?** Permite iniciar sesión con el correo y la contraseña del usuario.
- **¿Quién puede usarlo?** Cualquier usuario con credenciales válidas.
- **Datos que debes enviar:**
  - `username`: correo electrónico del usuario.
  - `password`: contraseña del usuario.
  - Ambos datos van en el cuerpo de la solicitud como formulario (`application/x-www-form-urlencoded`).
- **Encabezados obligatorios:**
  - `Content-Type: application/x-www-form-urlencoded`
- **Ejemplo de solicitud:**
```bash
curl --request POST \
     --url https://tu-servidor.com/auth/token \
     --header "Content-Type: application/x-www-form-urlencoded" \
     --data "username=usuario@correo.com" \
     --data "password=MiClave123"
```
- **Ejemplo de respuesta exitosa (código 200):**
```json
{
  "access_token": "jwt.token.generado",
  "token_type": "bearer"
}
```
- **Errores comunes:**
  - `401 Unauthorized`: el correo o la contraseña son incorrectos.

### 1.2 Generar el hash de una contraseña
- **Método y URL:** `POST /auth/hash-password`
- **¿Para qué sirve?** Crea un texto cifrado a partir de una contraseña, útil para tareas administrativas.
- **¿Quién puede usarlo?** Solo usuarios administradores.
- **Encabezados obligatorios:**
  - `Authorization: Bearer <token>` (usa el token obtenido en el punto 1.1).
  - `Content-Type: application/json`
- **Datos que debes enviar:**
```json
{
  "password": "TuNuevaContraseña"
}
```
- **Ejemplo de respuesta (200):**
```json
{
  "hashed_password": "cadena-cifrada"
}
```

## 2. Gestión de usuarios
### 2.1 Crear un usuario
- **Método y URL:** `POST /users/`
- **¿Para qué sirve?** Registrar un nuevo usuario en el sistema.
- **¿Quién puede usarlo?** Administradores.
- **Encabezados obligatorios:** `Authorization` y `Content-Type: application/json`.
- **Datos que debes enviar:**
```json
{
  "name": "Ana Pérez",
  "email": "ana.perez@correo.com",
  "role_id": 2
}
```
- **Respuesta exitosa (201):** devuelve la información del nuevo usuario y una contraseña temporal.
- **Errores comunes:**
  - `400 Bad Request`: el correo ya existe o faltan datos.

### 2.2 Consultar mi perfil
- **Método y URL:** `GET /users/me`
- **¿Para qué sirve?** Ver los datos del usuario que realizó la solicitud.
- **¿Quién puede usarlo?** Cualquier usuario autenticado.
- **Respuesta (200):** datos del usuario (nombre, correo, rol, etc.).

### 2.3 Listar usuarios
- **Método y URL:** `GET /users/`
- **¿Para qué sirve?** Obtener una lista de usuarios existentes.
- **¿Quién puede usarlo?** Administradores.
- **Parámetros opcionales (en la URL):**
  - `skip`: número de registros que se saltarán (por defecto 0).
  - `limit`: cantidad máxima de usuarios a devolver (por defecto 100).
- **Respuesta (200):** lista de usuarios paginada.

### 2.4 Ver un usuario específico
- **Método y URL:** `GET /users/{user_id}`
- **¿Para qué sirve?** Consultar los datos de un usuario concreto.
- **¿Quién puede usarlo?** Administradores.
- **Respuesta (200):** datos del usuario.

### 2.5 Actualizar un usuario
- **Método y URL:** `PUT /users/{user_id}`
- **¿Para qué sirve?** Modificar la información de un usuario.
- **¿Quién puede usarlo?** El propio usuario (para su registro) o un administrador.
- **Datos que puedes enviar:** cualquier combinación de los siguientes campos:
```json
{
  "name": "Nuevo Nombre",
  "role_id": 2,
  "is_active": true
}
```
- **Respuesta (200):** usuario actualizado.

### 2.6 Restablecer la contraseña de un usuario
- **Método y URL:** `POST /users/{user_id}/reset-password`
- **¿Para qué sirve?** Generar una contraseña temporal y obligar al usuario a cambiarla.
- **¿Quién puede usarlo?** Administradores.
- **Respuesta (200):** mensaje confirmando el envío de la contraseña temporal.

### 2.7 Eliminar un usuario
- **Método y URL:** `DELETE /users/{user_id}`
- **¿Para qué sirve?** Borrar un usuario del sistema.
- **¿Quién puede usarlo?** Administradores.
- **Respuesta (200):** confirmación de eliminación.

## 3. Plantillas (Templates)
Las plantillas definen la estructura de los datos que se cargarán.

### 3.1 Crear una plantilla
- **Método y URL:** `POST /templates/`
- **¿Quién puede usarlo?** Administradores.
- **Datos que debes enviar:**
```json
{
  "name": "Ventas 2024",
  "table_name": "ventas_2024",
  "description": "Plantilla para los reportes de ventas"
}
```
- **Respuesta (201):** datos de la plantilla creada.

### 3.2 Listar plantillas
- **Método y URL:** `GET /templates/`
- **Parámetros opcionales:** `skip`, `limit` (paginación).
- **Respuesta (200):** listado de plantillas.

### 3.3 Ver una plantilla específica
- **Método y URL:** `GET /templates/{template_id}`
- **Respuesta (200):** detalles de la plantilla.

### 3.4 Actualizar una plantilla
- **Método y URL:** `PUT /templates/{template_id}`
- **Datos posibles:**
```json
{
  "name": "Ventas Retail 2024",
  "description": "Actualización de alcance",
  "status": "active",
  "table_name": "ventas_retail_2024",
  "is_active": true
}
```
- **Respuesta (200):** plantilla actualizada.

### 3.5 Cambiar solo el estado
- **Método y URL:** `PATCH /templates/{template_id}/status`
- **Datos que debes enviar:**
```json
{
  "status": "inactive"
}
```
- **Respuesta (200):** estado actualizado.

### 3.6 Eliminar una plantilla
- **Método y URL:** `DELETE /templates/{template_id}`
- **Respuesta (200):** confirmación de eliminación.

### 3.7 Gestionar columnas de una plantilla
- **Agregar columnas:**
  - `POST /templates/{template_id}/columns`
  - Envía una columna o varias:
```json
{
  "columns": [
    {
      "name": "monto",
      "data_type": "decimal",
      "description": "Monto de la venta",
      "is_required": true
    }
  ]
}
```
- **Listar columnas:** `GET /templates/{template_id}/columns`
- **Ver una columna:** `GET /templates/{template_id}/columns/{column_id}`
- **Actualizar columna:** `PUT /templates/{template_id}/columns/{column_id}`
- **Eliminar columna:** `DELETE /templates/{template_id}/columns/{column_id}`

### 3.8 Administrar accesos a una plantilla
- **Conceder acceso:**
  - `POST /templates/{template_id}/access`
  - Datos:
```json
{
  "user_id": 5,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```
- **Listar accesos:** `GET /templates/{template_id}/access` (puedes usar `include_inactive=true` para ver accesos inactivos).
- **Revocar acceso:** `DELETE /templates/{template_id}/access/{access_id}`

### 3.9 Descargar el archivo base en Excel
- **Método y URL:** `GET /templates/{template_id}/excel`
- **¿Qué devuelve?** Un archivo `.xlsx` que sirve como base para completar la información según la plantilla.

## 4. Cargas de datos
### 4.1 Subir un archivo para validar
- **Método y URL:** `POST /templates/{template_id}/loads`
- **¿Para qué sirve?** Enviar un archivo con datos para que el sistema los valide.
- **¿Quién puede usarlo?** Usuarios que tengan acceso a la plantilla indicada.
- **Datos que debes enviar:** un archivo en el campo `file` (formulario tipo `multipart/form-data`).
- **Respuesta (202):** confirma que la carga fue registrada y está en proceso de validación.

### 4.2 Listar mis cargas
- **Método y URL:** `GET /loads`
- **Parámetros opcionales:** `template_id`, `skip`, `limit`.
- **Respuesta (200):** listado de cargas disponibles para el usuario.

### 4.3 Ver detalles de una carga
- **Método y URL:** `GET /loads/{load_id}`
- **Respuesta (200):** información de la carga, estado y resultados de validación.

### 4.4 Descargar el reporte de validación
- **Método y URL:** `GET /loads/{load_id}/report`
- **¿Qué devuelve?** Un archivo Excel con los resultados de la validación.

## 5. Archivos digitales
### 5.1 Listar archivos digitales
- **Método y URL:** `GET /digital-files/`
- **Parámetros opcionales:** `template_id`, `skip`, `limit`.
- **Respuesta (200):** lista de archivos almacenados.

### 5.2 Ver un archivo digital específico
- **Método y URL:** `GET /digital-files/{digital_file_id}`
- **Respuesta (200):** metadatos del archivo solicitado.

### 5.3 Obtener un archivo por plantilla
- **Método y URL:** `GET /digital-files/by-template/{template_id}`
- **Respuesta (200):** archivo relacionado con la plantilla indicada.

## 6. Registro de auditoría
### 6.1 Listar entradas de auditoría
- **Método y URL:** `GET /audit-logs/`
- **Parámetros opcionales:** `template_name` para filtrar por nombre de plantilla.
- **Respuesta (200):** lista de actividades registradas.

### 6.2 Ver una entrada específica
- **Método y URL:** `GET /audit-logs/{entry_id}`
- **Respuesta (200):** detalles de la entrada seleccionada.

### 6.3 Eliminar una entrada
- **Método y URL:** `DELETE /audit-logs/{entry_id}`
- **Respuesta (200):** confirmación de eliminación.

## 7. Reglas de validación
### 7.1 Crear una regla
- **Método y URL:** `POST /rules/`
- **Datos que debes enviar:**
```json
{
  "rule": "monto > 0",
  "is_active": true
}
```
- **Respuesta (201):** regla creada.

### 7.2 Listar reglas
- **Método y URL:** `GET /rules/`
- **Parámetros opcionales:** `skip`, `limit`.
- **Respuesta (200):** listado de reglas.

### 7.3 Ver una regla
- **Método y URL:** `GET /rules/{rule_id}`
- **Respuesta (200):** detalles de la regla.

### 7.4 Actualizar una regla
- **Método y URL:** `PUT /rules/{rule_id}`
- **Datos posibles:**
```json
{
  "rule": "monto >= 0",
  "is_active": false
}
```
- **Respuesta (200):** regla actualizada.

### 7.5 Eliminar una regla
- **Método y URL:** `DELETE /rules/{rule_id}`
- **Respuesta (200):** confirmación de eliminación.

## 8. Asistente inteligente
### 8.1 Solicitar análisis del asistente
- **Método y URL:** `POST /assistant/analyze`
- **¿Para qué sirve?** Pedir al asistente que analice información tomando en cuenta las reglas recientes.
- **Datos que debes enviar:**
```json
{
  "message": "Describe el estado de las validaciones"
}
```
- **Respuesta (200):** texto generado por el asistente con la interpretación solicitada.

---

## 9. Consejos finales
- Incluye siempre el encabezado `Authorization: Bearer <token>` en los endpoints que lo requieren.
- Repite el proceso de inicio de sesión cuando el token expire.
- Revisa los códigos de estado (200, 201, 400, 401, etc.) para entender si la operación fue exitosa o si faltó información.
- Si necesitas soporte adicional, comparte el código de error y la respuesta devuelta para que el equipo técnico pueda ayudarte.
