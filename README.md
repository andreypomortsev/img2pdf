# Image to PDF Conversion Service

A secure web service that converts images to PDF files and merges multiple PDFs into a single document. It features JWT authentication, a FastAPI backend, and Celery for asynchronous task processing, all running inside Docker containers.

## Features

- **JWT Authentication**: Secure access to all endpoints with token-based authentication
- **User Management**: Register and manage user accounts with secure password hashing
- **Asynchronous Image-to-PDF Conversion**: Upload an image, and it will be converted to a PDF in the background
- **Asynchronous PDF Merging**: Combine multiple PDF files into a single document
- **Task Status Tracking**: Monitor the status of any background task (conversion or merging)
- **Containerized**: The entire application stack is managed with Docker and Docker Compose for easy setup and deployment
- **Comprehensive Testing**: Includes unit and integration tests with high coverage

## Tech Stack

- **Backend**: FastAPI
- **Authentication**: JWT (JSON Web Tokens)
- **Asynchronous Tasks**: Celery
- **Message Broker**: Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Image Processing**: Pillow, img2pdf
- **PDF Manipulation**: pypdf
- **Security**: Passlib, OAuth2 with Password (and hashing)
- **Testing**: Pytest, HTTPX
- **Containerization**: Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/andreypomortsev/img2pdf.git
    cd img2pdf
    ```

2.  **Build and run the services:**
    ```bash
    docker compose up --build -d
    ```

3.  The application will be running and accessible at `http://localhost:8000`.

## Authentication

### Register a New User
- **URL**: `/api/v1/auth/register`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "your-secure-password"
  }
  ```
- **Success Response**:
  ```json
  {
    "email": "user@example.com",
    "id": 1,
    "is_active": true
  }
  ```

### Login
- **URL**: `/api/v1/auth/login`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "username": "user@example.com",
    "password": "your-secure-password"
  }
  ```
- **Success Response**:
  ```json
  {
    "access_token": "your-jwt-token",
    "token_type": "bearer"
  }
  ```

## API Endpoints

All endpoints below require authentication. Include the JWT token in the `Authorization` header:
```
Authorization: Bearer your-jwt-token
```

### Files

#### Upload an Image
- **URL**: `/api/v1/files/upload-image/`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
- **Form Data**: `file` (the image file to convert)
- **Success Response**:
  ```json
  {
    "task_id": "<your-task-id>",
    "status": "PENDING"
  }
  ```

#### Check Task Status
- **URL**: `/api/v1/files/tasks/{task_id}`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <token>`
- **Success Response**:
  ```json
  {
    "task_id": "<your-task-id>",
    "task_status": "SUCCESS",
    "task_result": "static/files/your_file.pdf"
  }
  ```

### PDF Operations

#### Merge PDFs
- **URL**: `/api/v1/pdfs/merge/`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <token>`
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
    "task_id": "<your-task-id>",
    "status": "PENDING"
  }
  ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
