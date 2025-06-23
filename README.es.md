# Servicio de Conversión de Imagen a PDF

Un servicio web que convierte imágenes a archivos PDF y fusiona múltiples PDFs en un solo documento. Utiliza un backend de FastAPI con Celery para el procesamiento asíncrono de tareas, todo ejecutándose dentro de contenedores de Docker.

## Características

- **Conversión Asíncrona de Imagen a PDF**: Sube una imagen y se convertirá a PDF en segundo plano.
- **Fusión Asíncrona de PDFs**: Combina múltiples archivos PDF en un solo documento.
- **Seguimiento del Estado de Tareas**: Monitorea el estado de cualquier tarea en segundo plano (conversión o fusión).
- **Contenerizado**: Toda la pila de la aplicación se gestiona con Docker y Docker Compose para una fácil configuración y despliegue.

## Tecnologías Utilizadas

- **Backend**: FastAPI
- **Tareas Asíncronas**: Celery
- **Broker de Mensajes**: Redis
- **Base de Datos**: PostgreSQL con SQLAlchemy ORM
- **Procesamiento de Imágenes**: Pillow, img2pdf
- **Manipulación de PDF**: PyPDF2
- **Contenerización**: Docker, Docker Compose

## Cómo Empezar

### Prerrequisitos

- Docker
- Docker Compose

### Ejecutando la Aplicación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/andreypomortsev/imgtopdf.git
    cd imgtopdf
    ```

2.  **Construye y ejecuta los servicios:**
    ```bash
    docker compose up --build -d
    ```

3.  La aplicación estará en funcionamiento y accesible en `http://localhost:8000`.

## Endpoints de la API

#### Subir una Imagen

- **URL**: `/api/v1/files/upload-image/`
- **Método**: `POST`
- **Datos del Formulario**: `file` (el archivo de imagen a convertir)
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-task-id>"
  }
  ```

#### Comprobar Estado de la Tarea

- **URL**: `/api/v1/files/tasks/{task_id}`
- **Método**: `GET`
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-task-id>",
    "task_status": "SUCCESS",
    "task_result": "static/files/tu_archivo.pdf"
  }
  ```

#### Fusionar PDFs

- **URL**: `/api/v1/pdfs/merge/`
- **Método**: `POST`
- **Cuerpo de la Petición**:
  ```json
  {
    "file_ids": [1, 2],
    "output_filename": "merged.pdf"
  }
  ```
- **Respuesta Exitosa**:
  ```json
  {
    "task_id": "<tu-task-id>"
  }
  ```

## Licencia

Este proyecto está bajo la Licencia MIT - consulta el archivo [LICENSE](LICENSE) para más detalles.
