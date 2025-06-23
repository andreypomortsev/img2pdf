from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from app.models.file import File as FileModel
from app.tasks import TEMP_DIR, convert_image_to_pdf, merge_pdfs


@patch("builtins.open", new_callable=mock_open, read_data=b"image content")
@patch("app.tasks.img2pdf.convert")
@patch("app.tasks.SessionLocal")
def test_convert_image_to_pdf(mock_session_local, mock_img2pdf_convert, mock_open_file):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_img2pdf_convert.return_value = b"pdf content"

    image_file = FileModel(id=1, filename="test.png", filepath="tmp/test-dir/test.png")
    mock_db.query.return_value.filter.return_value.first.return_value = image_file

    def mock_refresh(file_obj):
        file_obj.id = 99

    mock_db.refresh.side_effect = mock_refresh

    result_file_id = convert_image_to_pdf(1)

    mock_session_local.assert_called_once()
    mock_db.query.assert_called_once_with(FileModel)
    mock_open_file.assert_any_call("tmp/test-dir/test.png", "rb")
    mock_open_file.assert_any_call(Path("tmp/test-dir/test.pdf"), "wb")
    mock_img2pdf_convert.assert_called_once_with([b"image content"])

    assert result_file_id == 99
    added_file = mock_db.add.call_args[0][0]
    assert added_file.filename == "test.pdf"
    assert added_file.filepath == str(Path("tmp/test-dir/test.pdf"))

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    mock_db.close.assert_called_once()


@patch("app.tasks.Path.mkdir")
@patch("app.tasks.uuid.uuid4")
@patch("app.tasks.PdfMerger")
@patch("app.tasks.SessionLocal")
def test_merge_pdfs(mock_session_local, mock_pdf_merger_class, mock_uuid, mock_mkdir):
    mock_db = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_db

    mock_merger_instance = MagicMock()
    mock_pdf_merger_class.return_value = mock_merger_instance
    mock_uuid.return_value = "test-merge-uuid"

    mock_file_1 = FileModel(id=1, filename="test1.pdf", filepath="tmp/dir1/test1.pdf")
    mock_file_2 = FileModel(id=2, filename="test2.pdf", filepath="tmp/dir2/test2.pdf")
    mock_db.query.return_value.filter.return_value.all.return_value = [
        mock_file_1,
        mock_file_2,
    ]

    def mock_refresh(file_obj):
        file_obj.id = 100

    mock_db.refresh.side_effect = mock_refresh

    result_file_id = merge_pdfs([1, 2], "merged.pdf")

    mock_session_local.assert_called_once()
    mock_db.query.assert_called_once_with(FileModel)

    mock_merger_instance.append.assert_has_calls(
        [call("tmp/dir1/test1.pdf"), call("tmp/dir2/test2.pdf")]
    )

    expected_dir = TEMP_DIR / "test-merge-uuid"
    expected_filepath = expected_dir / "merged.pdf"
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_merger_instance.write.assert_called_once_with(str(expected_filepath))
    mock_merger_instance.close.assert_called_once()

    assert result_file_id == 100
    added_file = mock_db.add.call_args[0][0]
    assert added_file.filename == "merged.pdf"
    assert added_file.filepath == str(expected_filepath)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
