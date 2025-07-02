import io
import logging
import os
import sqlite3
import time
from pathlib import Path

from PIL import Image
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

# Enable SQL logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


# Print SQL statements to console
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(
    conn, cursor, statement, params, context, executemany
):
    conn.info.setdefault("query_start_time", []).append(time.time())
    print(f"\n=== SQL QUERY ===\n{statement}")
    if params:
        print(f"=== PARAMS ===\n{params}")


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(
    conn, cursor, statement, params, context, executemany
):
    total = time.time() - conn.info["query_start_time"].pop(-1)
    print(f"=== QUERY COMPLETE in {total:.6f}s ===\n")


from app.models.file import File as FileModel

# Polling mechanism removed - Celery tasks now run in eager mode during tests


def print_database_info(db_path: str):
    """Print detailed information about the SQLite database."""
    print(f"\n=== Database Info: {db_path} ===")
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")

    # For each table, show columns and row count
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")

        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print(f"  Columns: {[col[1] for col in columns]}")

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  Row count: {count}")

        # Show first few rows if any exist
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            rows = cursor.fetchall()
            print("  Sample rows:")
            for row in rows:
                print(f"    {row}")

    conn.close()


def test_merge_pdfs(
    authorized_client,
    db_engine,
    db_session,
    celery_db_session,
    tmp_path,
    test_user,
):
    """
    Test uploading multiple images, converting them, merging the resulting
    PDFs, and downloading the final merged PDF using filesystem.
    """
    print("\n=== Starting test_merge_pdfs ===")
    print(f"Test user ID: {test_user.id}")
    print(f"Test user email: {test_user.email}")

    # Print database info at the start of the test
    db_url = str(db_engine.url)
    print(f"\n=== Database Information ===")
    print(f"Database URL: {db_url}")

    if db_url.startswith("sqlite:///"):
        db_path = db_url[10:]  # Remove 'sqlite:///' prefix
        print(f"Database file path: {db_path}")
        print(f"Database file exists: {os.path.exists(db_path)}")

        # Print file permissions
        if os.path.exists(db_path):
            print(
                f"Database file permissions: {oct(os.stat(db_path).st_mode)[-3:]}"
            )

        print_database_info(db_path)

        # Print current working directory
        print(f"\n=== System Information ===")
        print(f"Current working directory: {os.getcwd()}")

        # List all SQLite files in /tmp
        print("\nSQLite files in /tmp:")
        tmp_files = [f for f in os.listdir("/tmp") if f.endswith(".sqlite")]
        if tmp_files:
            for f in tmp_files:
                print(f"  - {os.path.join('/tmp', f)}")
        else:
            print("  No SQLite files found in /tmp")

    # Verify the test user exists in the database
    print("\n=== Verifying test user in database ===")
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT id, email FROM users"))
        users = result.fetchall()
        print(f"Users in database: {users}")

        # Print all tables
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result]
        print(f"\nTables in database: {tables}")

        # Print schema of users table if it exists
        if "users" in tables:
            result = conn.execute(text("PRAGMA table_info(users)"))
            print("\nUsers table schema:")
            for row in result:
                print(f"  {row}")

    client = authorized_client
    pdf_file_ids = []
    created_files = []

    # Print test user info
    print(f"Test user: {test_user}")
    print(f"Test user email: {test_user.email}")
    print(f"Test user id: {test_user.id}")

    # Step 1: Generate a valid test image and upload it twice
    image = Image.new("RGB", (100, 100), color="red")
    image_bytes_io = io.BytesIO()
    image.save(image_bytes_io, format="PNG")
    image_content = image_bytes_io.getvalue()

    for i in range(1, 3):
        image_path = tmp_path / f"test_image_{i}.png"
        image_path.write_bytes(image_content)

        with open(image_path, "rb") as f:
            response = client.post(
                "/files/upload-image",
                files={"file": (image_path.name, f, "image/png")},
            )
        assert (
            response.status_code == 200
        ), f"Failed to upload image: {response.text}"
        upload_data = response.json()
        task_id = upload_data["task_id"]

        # Task should complete immediately in eager mode
        response = client.get(f"/files/task/{task_id}")
        assert (
            response.status_code == 200
        ), f"Failed to get task status: {response.text}"
        task_data = response.json()
        assert task_data["task_status"] == "SUCCESS"
        converted_pdf_id = task_data["task_result"]
        pdf_file_ids.append(converted_pdf_id)

    # Step 2: Merge the two PDFs
    assert len(pdf_file_ids) == 2
    merge_request_data = {
        "file_ids": pdf_file_ids,
        "output_filename": "merged_document.pdf",
    }
    response = client.post("/pdfs/merge/", json=merge_request_data)
    assert response.status_code == 200
    merge_task_data = response.json()
    merge_task_id = merge_task_data["task_id"]

    # Step 3: Check merge task status (should complete immediately in eager mode)
    response = client.get(f"/files/task/{merge_task_id}")
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["task_status"] == "SUCCESS"
    merged_pdf_id = task_data["task_result"]

    # Step 4: Verify the merged PDF exists and download it
    merged_file_db = (
        db_session.query(FileModel)
        .filter(FileModel.id == merged_pdf_id)
        .first()
    )
    assert merged_file_db is not None
    assert Path(merged_file_db.filepath).exists()
    created_files.append(Path(merged_file_db.filepath))

    response = client.get(f"/files/{merged_pdf_id}")
    assert response.status_code == 200
    expected_disposition = 'attachment; filename="merged_document.pdf"'
    assert response.headers["content-disposition"] == expected_disposition
    assert response.content.startswith(b"%PDF-")

    # Step 5: Clean up all created files
    for file_id in pdf_file_ids:
        file_db = (
            db_session.query(FileModel).filter(FileModel.id == file_id).first()
        )
        if file_db and Path(file_db.filepath).exists():
            created_files.append(Path(file_db.filepath))

    for f in created_files:
        if f.exists():
            f.unlink()
