"""PDF generation functionality."""

import io
from pathlib import Path
from typing import BinaryIO, List, Union

from PIL import Image
from pypdf import PdfReader, PdfWriter

import img2pdf


class PDFGenerator:
    """Handles PDF generation and manipulation operations."""

    @staticmethod
    def image_to_pdf(
        image_data: Union[bytes, BinaryIO], output_path: Path
    ) -> Path:
        """
        Convert an image to a PDF file.

        Args:
            image_data: Binary image data or file-like object
            output_path: Path where the PDF will be saved

        Returns:
            Path to the generated PDF file

        Raises:
            ValueError: If the image data is invalid or conversion fails
            IOError: If there's an error writing the output file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Convert image to PDF using img2pdf
            with open(output_path, "wb") as f:
                try:
                    if isinstance(image_data, bytes):
                        f.write(img2pdf.convert(image_data))
                    else:
                        # Reset file pointer to start in case it was read before
                        if hasattr(image_data, "seek") and hasattr(
                            image_data, "tell"
                        ):
                            if image_data.tell() > 0:
                                image_data.seek(0)
                        f.write(img2pdf.convert(image_data.read()))
                except img2pdf.ImageOpenError as e:
                    raise ValueError(
                        f"Failed to convert image to PDF: {str(e)}"
                    ) from e
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert image to PDF: {str(e)}"
                    ) from e

            return output_path
        except IOError as e:
            raise IOError(f"Failed to write PDF file: {str(e)}") from e

    @staticmethod
    def merge_pdfs(pdf_paths: List[Path], output_path: Path) -> Path:
        """
        Merge multiple PDF files into a single PDF.

        Args:
            pdf_paths: List of paths to PDF files to merge
            output_path: Path where the merged PDF will be saved

        Returns:
            Path to the merged PDF file

        Raises:
            ValueError: If no PDF files are provided to merge
            FileNotFoundError: If any input PDF file does not exist
        """
        print("\n=== INSIDE merge_pdfs ===")
        print(f"pdf_paths: {pdf_paths}")
        print(f"output_path: {output_path}")

        if not pdf_paths:
            raise ValueError("No PDF files to merge")

        # Ensure all input files exist before starting
        for pdf_path in pdf_paths:
            print(f"Checking if {pdf_path} exists")
            if not pdf_path.exists():
                print(f"File not found: {pdf_path}")
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        print("Creating PdfWriter instance")
        writer = PdfWriter()
        print(f"PdfWriter instance created: {writer}")

        try:
            for i, pdf_path in enumerate(pdf_paths, 1):
                print(f"Processing PDF {i}/{len(pdf_paths)}: {pdf_path}")
                reader = PdfReader(str(pdf_path))
                print(f"  PDF has {len(reader.pages)} pages")

                # Add all pages from this PDF to the writer
                for page in reader.pages:
                    writer.add_page(page)
                print(f"  Successfully added pages from: {pdf_path}")

            # Ensure output directory exists
            print(f"Ensuring output directory exists: {output_path.parent}")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write merged PDF to output path
            print(f"Writing merged PDF to: {output_path}")
            with open(str(output_path), "wb") as output_file:
                writer.write(output_file)
            print("Successfully wrote merged PDF")
            return output_path
        finally:
            writer.close()

    @staticmethod
    def create_blank_page(width: int = 612, height: int = 792) -> bytes:
        """
        Create a blank PDF page with the specified dimensions.

        Args:
            width: Page width in points (default: 8.5in * 72dpi = 612)
            height: Page height in points (default: 11in * 72dpi = 792)

        Returns:
            Bytes containing the PDF data
        """
        # Create a blank white image
        img = Image.new("RGB", (width, height), color="white")

        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PDF")
        return img_byte_arr.getvalue()
