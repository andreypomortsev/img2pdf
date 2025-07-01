from unittest.mock import MagicMock, mock_open, patch

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File as FileModel
from app.services.file_service import TEMP_DIR, FileService


class TestFileService:
    """Unit tests for the FileService, with all externals mocked."""

    def setup_method(self):
        """Set up the test environment before each test."""
        self.file_service = FileService()
        self.db_session = MagicMock(spec=Session)

    @patch("builtins.open", new_callable=mock_open)
    @patch("app.services.file_service.uuid.uuid4")
    def test_save_file(self, mock_uuid, mock_open_file):
        """
        Test that save_file correctly handles file I/O and DB interactions.
        """
        # Setup
        # Create a fixed UUID for testing
        test_uuid = "test-uuid-1234"
        test_uuid_obj = MagicMock()
        test_uuid_obj.hex = test_uuid
        mock_uuid.return_value = test_uuid_obj

        # Create a mock for the uploaded file
        mock_upload_file = MagicMock(spec=UploadFile)
        mock_upload_file.filename = "test.png"
        # Create a mock for the file attribute
        mock_file = MagicMock()
        mock_file.read.return_value = b"test content"
        # Set the file attribute on the mock_upload_file
        type(mock_upload_file).file = mock_file

        # Mock the FileModel to avoid DB operations
        with patch("app.services.file_service.FileModel") as mock_file_model:
            # Create a mock DB file object
            mock_db_file = MagicMock()
            mock_db_file.id = 1
            mock_db_file.filename = "test.png"
            expected_filepath = str(TEMP_DIR / test_uuid / "test.png")
            mock_db_file.filepath = expected_filepath
            mock_file_model.return_value = mock_db_file

            # Create a context manager for the open mock
            mock_file_handle = MagicMock()
            mock_open_file.return_value.__enter__.return_value = (
                mock_file_handle
            )

            # Create a mock for the mkdir method
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                # Execute
                db_file = self.file_service.save_file(
                    db=self.db_session,
                    file=mock_upload_file,
                    owner_id=1,
                    content_type="image/png",
                )

                # Verify mkdir was called with the right arguments
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

            # Verify file operations
            assert mock_open_file.called
            mock_file_handle.write.assert_called_once_with(b"test content")

            # Verify database operations
            mock_file_model.assert_called_once()
            self.db_session.add.assert_called_once_with(mock_db_file)
            self.db_session.flush.assert_called_once()
            self.db_session.refresh.assert_called_once_with(mock_db_file)

            # Verify the returned file object
            assert db_file == mock_db_file

    def test_get_file_by_id(self):
        """
        Test that get_file_by_id correctly queries the database using a mock session.
        """
        # Setup
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_superuser = False

        mock_file = FileModel(
            id=1, filename="test.pdf", filepath="/tmp/test.pdf", owner_id=1
        )

        # Create a mock query object
        mock_query = MagicMock()
        # Set up the filter chain
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_file
        mock_query.filter.return_value = mock_filter
        self.db_session.query.return_value = mock_query

        # Execute
        db_file = self.file_service.get_file_by_id(
            db=self.db_session, file_id=1, current_user=mock_user
        )

        # Assert
        # Verify the query was made with FileModel
        self.db_session.query.assert_called_once_with(FileModel)

        # Verify filter was called once with the file ID
        mock_query.filter.assert_called_once()

        # Get the filter condition
        filter_condition = mock_query.filter.call_args[0][0]

        # Verify the filter condition is for the file ID
        assert "id = :id_1" in str(filter_condition)

        # Verify the query was executed
        mock_filter.first.assert_called_once()

        # Verify the returned file matches our mock
        assert db_file == mock_file

    @patch("app.services.file_service.merge_pdfs.delay")
    def test_create_merge_task(self, mock_delay):
        """
        Test that create_merge_task correctly calls the Celery task.
        """
        # Setup
        file_ids = [1, 2]
        output_filename = "merged.pdf"

        # Execute
        self.file_service.create_merge_task(
            file_ids=file_ids, output_filename=output_filename
        )

        # Assert
        mock_delay.assert_called_once_with(file_ids, output_filename)
