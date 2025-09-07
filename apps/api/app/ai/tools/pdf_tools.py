from typing import List
from pathlib import Path
import tempfile
from langchain_core.documents import Document


class PDFExtractionTool:
    """Tool for extracting text and metadata from PDF documents using Unstructured."""

    def __init__(self):
        """Initialize PDF extraction tool."""
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        try:
            from unstructured.partition.pdf import partition_pdf

            print("[PDF_EXTRACTION_TOOL] Unstructured library available")
        except ImportError as e:
            raise ImportError(f"Unstructured library not available: {str(e)}")

    def extract_text(
        self, file_path: str, original_filename: str = None
    ) -> List[Document]:
        """
        Extract text from PDF using Unstructured with OCR capabilities.

        Args:
            file_path: Path to PDF file
            original_filename: Original filename for metadata

        Returns:
            List of Document objects, one per page

        Raises:
            ValueError: If extraction fails
        """
        source_filename = original_filename or Path(file_path).name

        print(f"[PDF_EXTRACTION_TOOL] Using Unstructured for {source_filename}")

        try:
            from unstructured.partition.pdf import partition_pdf

            # Create a temporary directory for any file operations
            with tempfile.TemporaryDirectory() as temp_dir:
                # Use Unstructured to partition the PDF with OCR
                elements = partition_pdf(
                    filename=file_path,
                    strategy="hi_res",  # High resolution strategy for better OCR
                    infer_table_structure=True,  # Extract table structure
                    extract_images_in_pdf=False,  # Don't extract images to avoid permission issues
                    extract_image_block_types=[],  # Don't extract image blocks
                    extract_image_block_to_payload=False,  # Don't include image data
                    include_page_breaks=True,  # Include page break information
                    output_dir_path=temp_dir,  # Use temporary directory
                )

                # Group elements by page
                pages_content = {}
                for element in elements:
                    # Get page number (Unstructured uses 1-based indexing)
                    page_num = getattr(element.metadata, "page_number", 1)

                    # Handle None page numbers
                    if page_num is None:
                        page_num = 1

                    if page_num not in pages_content:
                        pages_content[page_num] = []

                    # Add element text to page content
                    if (
                        hasattr(element, "text")
                        and element.text
                        and element.text.strip()
                    ):
                        pages_content[page_num].append(element.text)

                # Create Document objects for each page
                documents = []
                for page_num in sorted(pages_content.keys()):
                    page_content = "\n".join(pages_content[page_num])

                    doc = Document(
                        page_content=page_content,
                        metadata={
                            "file_type": "pdf",
                            "file_path": file_path,
                            "source_file": source_filename,
                            "page_number": page_num,
                            "extraction_method": "Unstructured_Hi_Res_OCR",
                            "total_pages": len(pages_content),
                            "has_tables": any(
                                "table" in str(type(elem)).lower()
                                for elem in elements
                                if getattr(elem.metadata, "page_number", 1) == page_num
                            ),
                            "element_count": len(
                                [
                                    elem
                                    for elem in elements
                                    if getattr(elem.metadata, "page_number", 1)
                                    == page_num
                                ]
                            ),
                        },
                    )
                    documents.append(doc)

                print(
                    f"[PDF_EXTRACTION_TOOL] Successfully extracted {len(documents)} pages from {source_filename}"
                )
                return documents

        except ImportError as e:
            raise ValueError(f"Unstructured library not available: {str(e)}")
        except Exception as e:
            print(
                f"[PDF_EXTRACTION_TOOL] Extraction failed for {source_filename}: {str(e)}"
            )
            raise ValueError(f"PDF extraction failed: {str(e)}")
