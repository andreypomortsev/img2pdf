from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_engine
from app.schemas.user import UserCreate


def init_db() -> None:
    """
    Initialize the database with initial data.

    This function creates database tables if they don't exist and creates
    an initial superuser if it doesn't exist.
    """
    # Get the engine
    engine = get_engine()

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create a database session
    db = Session(bind=engine)

    try:
        # Skip if we're in testing mode or if the first superuser is not configured
        if (
            settings.TESTING
            or not settings.FIRST_SUPERUSER_EMAIL
            or not settings.FIRST_SUPERUSER_PASSWORD
        ):
            return

        # Check if the user already exists
        user = crud.get_user_by_email(db, email=settings.FIRST_SUPERUSER_EMAIL)

        if not user:
            # Create first superuser
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER_EMAIL,
                username=settings.FIRST_SUPERUSER_EMAIL.split("@")[0],
                password=settings.FIRST_SUPERUSER_PASSWORD,
                full_name="Initial Superuser",
                is_superuser=True,
            )
            user = crud.create_user(db, user=user_in)
            print(f"Created superuser {user.email}")
        else:
            # Update existing user to ensure they're a superuser
            if not user.is_superuser:
                user.is_superuser = True
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"Updated user {user.email} to superuser")
    except Exception as e:
        print(f"Error creating initial superuser: {e}")
    finally:
        db.close()
