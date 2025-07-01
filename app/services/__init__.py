"""Services package initialization."""

from app.interfaces.task_service_interface import TaskServiceInterface
from app.services.pdf_service import PDFService
from app.services.task_service import TaskService

# Initialize task service
task_service = TaskService()

# Initialize PDF service with task service dependency
pdf_service = PDFService(task_service=task_service)

__all__ = [
    "task_service",
    "pdf_service",
    "TaskService",
    "PDFService",
    "TaskServiceInterface",
]
