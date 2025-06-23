# Image to PDF Conversion Service

A web service that converts images to PDF files and merges multiple PDFs into a single document. It uses a FastAPI backend with Celery for asynchronous task processing, all running inside Docker containers.

## Features

- **Asynchronous Image-to-PDF Conversion**: Upload an image, and it will be converted to a PDF in the background.
- **Asynchronous PDF Merging**: Combine multiple PDF files into a single document.
- **Task Status Tracking**: Monitor the status of any background task (conversion or merging).
- **Containerized**: The entire application stack is managed with Docker and Docker Compose for easy setup and deployment.

## Tech Stack

- **Backend**: FastAPI
- **Asynchronous Tasks**: Celery
- **Message Broker**: Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Image Processing**: Pillow, img2pdf
- **PDF Manipulation**: PyPDF2
- **Containerization**: Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/andreypomortsev/imgtopdf.git
    cd imgtopdf
    ```

2.  **Build and run the services:**
    ```bash
    docker compose up --build -d
    ```

3.  The application will be running and accessible at `http://localhost:8000`.

## API Endpoints

#### Upload an Image

- **URL**: `/api/v1/files/upload-image/`
- **Method**: `POST`
- **Form Data**: `file` (the image file to convert)
- **Success Response**:
  ```json
  {
    "task_id": "<your-task-id>"
  }
  ```

#### Check Task Status

- **URL**: `/api/v1/files/tasks/{task_id}`
- **Method**: `GET`
- **Success Response**:
  ```json
  {
    "task_id": "<your-task-id>",
    "task_status": "SUCCESS",
    "task_result": "static/files/your_file.pdf"
  }
  ```

#### Merge PDFs

- **URL**: `/api/v1/pdfs/merge/`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "file_ids": [1, 2],
    "output_filename": "merged.pdf"
  }
  ```
- **Success Response**:
  ```json
  {
    "task_id": "<your-task-id>"
  }
  ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
