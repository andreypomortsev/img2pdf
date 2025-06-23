import os
from typing import List

import img2pdf
from PyPDF2 import PdfMerger

from app.db.session import SessionLocal
from app.models.file import File as FileModel
from app.worker import celery_app


@celery_app.task
def convert_image_to_pdf(file_id: int):
    db = SessionLocal()
    try:
        db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
        if not db_file:
            return f"File with id {file_id} not found."

        image_path = db_file.filepath
        pdf_path = os.path.splitext(image_path)[0] + ".pdf"

        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_path))

        # Update the file record with the PDF path
        db_file.filepath = pdf_path
        db.add(db_file)
        db.commit()

        return pdf_path
    finally:
        db.close()


@celery_app.task
def merge_pdfs(file_ids: List[int], output_filename: str):
    db = SessionLocal()
    merger = PdfMerger()
    try:
        files = db.query(FileModel).filter(FileModel.id.in_(file_ids)).all()
        if len(files) != len(file_ids):
            found_ids = {file.id for file in files}
            missing_ids = set(file_ids) - found_ids
            return f"Files with ids {list(missing_ids)} not found."

        for db_file in files:
            if not db_file.filepath.lower().endswith(".pdf"):
                return f"File {db_file.filename} is not a PDF."
            merger.append(db_file.filepath)

        output_dir = "static/files"
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "wb") as f:
            merger.write(f)
        merger.close()

        new_db_file = FileModel(filename=output_filename, filepath=output_path)
        db.add(new_db_file)
        db.commit()
        db.refresh(new_db_file)

        return new_db_file.filepath
    finally:
        db.close()
