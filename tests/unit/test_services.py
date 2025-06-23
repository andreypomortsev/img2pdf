from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File as FileModel
from app.services.file_service import TEMP_DIR, FileService


@pytest.fixture
def file_service():
    return FileService()


@pytest.fixture
def db_session():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_upload_file():
    return MagicMock(spec=UploadFile)


@patch("builtins.open", new_callable=mock_open)
@patch("app.services.file_service.Path.mkdir")
@patch("app.services.file_service.uuid.uuid4")
def test_save_file(
    mock_uuid, mock_mkdir, mock_open_file, file_service, db_session, mock_upload_file
):
    mock_uuid.return_value = "test-uuid"
    mock_upload_file.filename = "test.png"
    mock_upload_file.file = MagicMock()
    mock_upload_file.file.read.return_value = b"test content"

    db_file = file_service.save_file(db=db_session, file=mock_upload_file)

    expected_dir = TEMP_DIR / "test-uuid"
    expected_filepath = expected_dir / "test.png"

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_file.assert_called_once_with(expected_filepath, "wb")
    mock_open_file().write.assert_called_once_with(b"test content")

    assert db_file.filename == "test.png"
    assert db_file.filepath == str(expected_filepath)
    db_session.add.assert_called_once_with(db_file)
    db_session.flush.assert_called_once()
    db_session.refresh.assert_called_once_with(db_file)


def test_get_file_by_id(file_service: FileService, db_session: Session):
    db_session.query.return_value.filter.return_value.first.return_value = FileModel(
        id=1, filename="test.pdf", filepath="/tmp/test.pdf"
    )

    db_file = file_service.get_file_by_id(db=db_session, file_id=1)

    assert db_file is not None
    assert db_file.id == 1
    assert db_file.filename == "test.pdf"


@patch("app.services.file_service.merge_pdfs")
def test_create_merge_task(mock_merge_pdfs, file_service: FileService):
    file_ids = [1, 2]
    output_filename = "merged.pdf"

    task = file_service.create_merge_task(file_ids, output_filename)

    mock_merge_pdfs.delay.assert_called_once_with(file_ids, output_filename)
    assert task is not None
