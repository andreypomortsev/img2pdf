# Import models to make them available when importing from app.models
from app.models.file import File  # noqa: F401
from app.models.user import User  # noqa: F401

# This makes the models available for SQLAlchemy's metadata
try:
    from app.db.base_class import Base  # noqa: F401
except ImportError:
    # Handle case where base.py hasn't been created yet
    pass

# This makes the models available for import like: from app.models import User, File
__all__ = ["User", "File"]
