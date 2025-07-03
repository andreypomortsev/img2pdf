# Servicio de Conversión de Imagen a PDF

Un servicio web seguro que convierte imágenes a archivos PDF y fusiona múltiples PDFs en un solo documento. Incluye autenticación JWT, un backend de FastAPI y Celery para el procesamiento asíncrono de tareas, todo ejecutándose dentro de contenedores de Docker.

## Características

- **Autenticación JWT**: Acceso seguro a todos los endpoints con autenticación basada en tokens
- **Gestión de Usuarios**: Registro y administración de cuentas con hash seguro de contraseñas
- **Conversión Asíncrona de Imagen a PDF**: Sube una imagen y se convertirá a PDF en segundo plano
- **Fusión Asíncrona de PDFs**: Combina múltiples archivos PDF en un solo documento
- **Seguimiento del Estado de Tareas**: Monitorea el estado de cualquier tarea en segundo plano (conversión o fusión)
- **Contenerizado**: Toda la pila de la aplicación se gestiona con Docker y Docker Compose para una fácil configuración y despliegue
- **Pruebas Integrales**: Incluye pruebas unitarias y de integración con alta cobertura

## Tecnologías Utilizadas

- **Backend**: FastAPI
- **Autenticación**: JWT (JSON Web Tokens)
- **Tareas Asíncronas**: Celery
- **Broker de Mensajes**: Redis
- **Base de Datos**: PostgreSQL con SQLAlchemy ORM
- **Procesamiento de Imágenes**: Pillow, img2pdf
- **Manipulación de PDF**: pypdf
- **Seguridad**: Passlib, OAuth2 con Contraseña (y hashing)
- **Pruebas**: Pytest, HTTPX
- **Contenedores**: Docker, Docker Compose

## Cómo Empezar

### Prerrequisitos

- Docker
- Docker Compose

### Ejecutando la Aplicación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/andreypomortsev/img2pdf.git
    cd img2pdf
    ```

2.  **Construye y ejecuta los servicios:**
    ```bash
    docker compose up --build -d
    ```

3.  La aplicación estará en funcionamiento y accesible en `http://localhost:8000`.

## Autenticación

### Registrar un Nuevo Usuario
- **URL**: `/api/v1/auth/register`
- **Método**: `POST`
- **Cuerpo**:
  ```json
  {
    "email": "usuario@ejemplo.com",
    "password": "tu-contraseña-segura"
  }
  ```
- **Respuesta Exitosa**:
  ```json
  {
    "email": "usuario@ejemplo.com",
    "id": 1,
    "is_active": true
  }
  ```

### Iniciar Sesión
- **URL**: `/api/v1/auth/login`
- **Método**: `POST`
- **Cuerpo**:
  ```json
  {
    "username": "usuario@ejemplo.com",
    "password": "tu-contraseña-segura"
  }
  ```
- **Respuesta Exitosa**:
  ```json
  {
    "access_token": "tu-token-jwt",
    "token_type": "bearer"
  }
  ```

## Documentación de la API

Todos los endpoints siguientes requieren autenticación. Incluye el token JWT en la cabecera `Authorization`:
```
Authorization: Bearer tu-token-jwt
```

### Archivos

#### Subir una Imagen
- **URL**: `/api/v1/files/upload-image/`
- **Método**: `POST`
- **Cabeceras**: `Authorization: Bearer <token>`
- **Datos del Formulario**: `file` (el archivo de imagen a convertir)
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-id-de-tarea>",
    "status": "PENDING"
  }
  ```

#### Verificar Estado de Tarea
- **URL**: `/api/v1/files/tasks/{task_id}`
- **Método**: `GET`
- **Cabeceras**: `Authorization: Bearer <token>`
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-id-de-tarea>",
    "task_status": "SUCCESS",
    "task_result": "static/files/tu_archivo.pdf"
  }
  ```

### Operaciones con PDFs

#### Fusionar PDFs
- **URL**: `/api/v1/pdfs/merge/`
- **Método**: `POST`
- **Cabeceras**: `Authorization: Bearer <token>`
- **Cuerpo**:
  ```json
  {
    "file_ids": [1, 2],
    "output_filename": "combinado.pdf"
  }
  ```
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-id-de-tarea>",
    "status": "PENDING"
  }
  ```

## Licencia

Este proyecto está bajo la Licencia MIT - consulta el archivo [LICENSE](LICENSE) para más detalles.
