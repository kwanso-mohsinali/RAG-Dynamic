from langchain_community.document_loaders import UnstructuredExcelLoader
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from langchain_core.documents import Document


class ExcelExtractionTool:
    """
    Tool for memory-efficient Excel data extraction.
    """

    def __init__(self):
        self.supported_extensions = [".xlsx", ".xls", ".xlsm"]

    def extract_text(
        self,
        file_path: str,
        original_filename: str = None,
    ) -> List[Document]:
        """
        Extract financial data from Excel file with memory optimization.

        Args:
            file_path: Path to Excel file
            max_memory_mb: Maximum additional memory usage allowed (MB)

        Returns:
            Dictionary containing extracted data and metadata
        """

        print(f"[EXCEL_EXTRACTION] Starting extraction: {file_path}")

        try:
            # Validate file
            if not self._validate_excel_file(file_path):
                raise ValueError(f"Invalid Excel file: {file_path}")

            # Get file info
            excel_info = self._get_excel_info(file_path)
            print(f"[EXCEL_EXTRACTION] File size: {excel_info['size_mb']:.2f}MB")

            loader = UnstructuredExcelLoader(
                file_path,
                mode="elements",  # Extract as separate elements
            )

            # Load documents
            documents = loader.load()
            print(
                f"[EXCEL_EXTRACTION] Extracted {len(documents)} documents from {file_path}"
            )
            source_filename = original_filename or excel_info["filename"]
            print(f"[EXCEL_EXTRACTION] Source filename: {source_filename}")

            for doc in documents:
                doc.metadata.update(
                    {
                        "file_type": "excel",
                        "file_path": file_path,
                        "source_file": source_filename,  # Use original filename
                        "extraction_method": "UnstructuredExcelLoader",
                    }
                )

            return documents

        except Exception as e:
            print(f"[EXCEL_EXTRACTION] Extraction failed: {str(e)}")
            raise RuntimeError(f"Excel extraction failed: {str(e)}")

    def _validate_excel_file(self, file_path: str) -> bool:
        """Validate Excel file format and accessibility."""

        path = Path(file_path)

        if not path.exists():
            return False

        if path.suffix.lower() not in self.supported_extensions:
            return False

        if path.stat().st_size == 0:
            return False

        return True

    def _get_excel_info(self, file_path: str) -> Dict[str, Any]:
        """Get Excel file metadata."""

        path = Path(file_path)
        stat = path.stat()

        return {
            "filename": path.name,
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "extension": path.suffix.lower(),
            "version": "xlsx" if path.suffix.lower() == ".xlsx" else "legacy",
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
